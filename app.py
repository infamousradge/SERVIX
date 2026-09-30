import tkinter as tk
from tkinter import ttk, messagebox, filedialog
from pathlib import Path
import csv
import shutil
import zipfile
import json
import datetime
from database import connect, init_db, next_code, now, today, get_setting, set_setting, DB, DATA_ROOT, ROLES, authenticate, hash_password, can, audit, repeat_complaints
from attachment_utils import store_attachment
from service_repository import add_history, add_part, upsert_calibration, add_attachment
from service_report import create_service_report

ROOT=Path(__file__).resolve().parent
NAVY='#071A3D'; NAVY2='#0C2B5B'; BLUE='#0876D1'; CYAN='#11B6D8'; GREEN='#48C774'; BG='#F3F7FB'; CARD='#FFFFFF'; TEXT='#142033'; MUTED='#6E7B8D'; BORDER='#DDE6F0'; RED='#D9534F'; ORANGE='#F0A23B'

class Servix(tk.Tk):
    def __init__(self):
        super().__init__(); init_db()
        self.title('HAC — Service Management System'); self.geometry('1536x960'); self.minsize(1280,760); self.configure(bg=BG)
        self.style=ttk.Style(self); self.style.theme_use('clam')
        self.option_add('*Font','{Segoe UI} 8')
        self.option_add('*TCombobox*Listbox.font','{Segoe UI} 8')
        self.style.configure('Treeview',font=('Segoe UI',8),rowheight=24,background='white',fieldbackground='white',borderwidth=0)
        self.style.configure('Treeview.Heading',font=('Segoe UI',8,'bold'),background='#EAF1F8',foreground=TEXT,padding=5)
        self.style.map('Treeview',background=[('selected','#D9ECFF')],foreground=[('selected',TEXT)])
        self.style.configure('TLabel',font=('Segoe UI',8)); self.style.configure('TButton',font=('Segoe UI',8))
        self.style.configure('TEntry',font=('Segoe UI',8),padding=3); self.style.configure('TCombobox',font=('Segoe UI',8),padding=2)
        self.style.configure('TNotebook',background=BG,borderwidth=0)
        self.style.configure('TNotebook.Tab',font=('Segoe UI',8,'bold'),padding=(9,5),background='#EAF1F8',foreground=MUTED)
        self.style.map('TNotebook.Tab',background=[('selected','white')],foreground=[('selected',BLUE)])
        self.current_user=None; self.withdraw()
        if not self.login(): self.destroy(); return
        self.deiconify(); self.page=None; self.build_shell(); self.run_auto_backup(); self.show_dashboard()

    def run_auto_backup(self):
        if get_setting('auto_backup_enabled','1')!='1': return
        try:
            days=max(1,int(get_setting('auto_backup_days','1') or 1)); keep=max(1,int(get_setting('auto_backup_keep','14') or 14))
            with connect() as con:last=con.execute("SELECT backup_date FROM backup_history WHERE status='Success' AND notes LIKE 'Automatic backup%' ORDER BY id DESC LIMIT 1").fetchone()
            if last:
                stamp=datetime.datetime.fromisoformat(last['backup_date'])
                if datetime.datetime.now()-stamp<datetime.timedelta(days=days):return
            folder=DATA_ROOT/'backups'; folder.mkdir(parents=True,exist_ok=True)
            dest=folder/('SERVIX_AutoBackup_'+datetime.datetime.now().strftime('%Y%m%d_%H%M%S')+'.zip')
            with connect() as con:con.execute('PRAGMA wal_checkpoint(FULL)')
            with zipfile.ZipFile(dest,'w',zipfile.ZIP_DEFLATED) as z:
                z.write(DB,'data/servix.db'); att=DATA_ROOT/'attachments'
                if att.exists():
                    for p in att.rglob('*'):
                        if p.is_file():z.write(p,'attachments/'+str(p.relative_to(att)))
                z.writestr('manifest.json',json.dumps({'product':'SERVIX','created':datetime.datetime.now().isoformat(timespec='seconds'),'database':'data/servix.db','automatic':True},indent=2))
            with connect() as con:con.execute('INSERT INTO backup_history(backup_date,filename,status,notes) VALUES(?,?,?,?)',(now(),str(dest),'Success','Automatic backup on application start'))
            backups=sorted(folder.glob('SERVIX_AutoBackup_*.zip'),key=lambda p:p.stat().st_mtime,reverse=True)
            for old in backups[keep:]:
                try:old.unlink()
                except OSError:pass
            audit(self.current_user['username'],'backup',dest.name,'AUTO_CREATE','Automatic backup created')
        except Exception as ex:
            try:
                with connect() as con:con.execute('INSERT INTO backup_history(backup_date,filename,status,notes) VALUES(?,?,?,?)',(now(),'Automatic backup','Failed',str(ex)[:250]))
            except Exception:pass

    def login(self):
        with connect() as con:
            admin=con.execute("SELECT * FROM users WHERE username='admin'").fetchone()
        if admin and not admin['password_hash']:
            if not self.set_initial_password(admin['id']): return False
        result={'ok':False}
        d=tk.Toplevel(self); d.title('SERVIX Login'); d.geometry('390x300'); d.resizable(False,False); d.configure(bg=CARD)
        tk.Label(d,text='SERVIX',bg=CARD,fg=NAVY,font=('Segoe UI',22,'bold')).pack(pady=(25,2))
        tk.Label(d,text='Sign in to Service Management System',bg=CARD,fg=MUTED,font=('Segoe UI',8)).pack(pady=(0,14))
        tk.Label(d,text='Username',bg=CARD,fg=TEXT).pack(anchor='w',padx=45); user=ttk.Entry(d); user.pack(fill='x',padx=45,pady=(3,9)); user.insert(0,'admin')
        tk.Label(d,text='Password',bg=CARD,fg=TEXT).pack(anchor='w',padx=45); pwd=ttk.Entry(d,show='*'); pwd.pack(fill='x',padx=45,pady=(3,10))
        msg=tk.Label(d,text='',bg=CARD,fg=RED,font=('Segoe UI',7)); msg.pack()
        def submit(*_):
            row=authenticate(user.get(),pwd.get())
            if not row: msg.config(text='Invalid username/password or disabled account.'); return
            self.current_user={k:row[k] for k in ('id','username','display_name','role')}; audit(row['username'],'session',row['id'],'LOGIN','Successful login')
            if row['must_change_password'] and not self.change_password(row['id'],row['username'],forced=True): return
            result['ok']=True; d.destroy()
        tk.Button(d,text='Sign In',command=submit,bg=BLUE,fg='white',bd=0,padx=30,pady=7).pack(pady=8)
        pwd.bind('<Return>',submit); d.grab_set(); user.focus_set(); self.wait_window(d)
        return result['ok']

    def change_password(self,user_id,username,forced=False):
        result={'ok':False}; d=tk.Toplevel(self); d.title('Change Password'); d.geometry('430x300'); d.resizable(False,False); d.configure(bg=CARD)
        tk.Label(d,text='Change Password',bg=CARD,fg=NAVY,font=('Segoe UI',14,'bold')).pack(pady=(22,5))
        tk.Label(d,text='A new password is required before continuing.' if forced else 'Set a new SERVIX password.',bg=CARD,fg=MUTED).pack(pady=(0,12))
        p1=ttk.Entry(d,show='*'); p2=ttk.Entry(d,show='*')
        for label,w in [('New Password (minimum 8 characters)',p1),('Confirm Password',p2)]:
            tk.Label(d,text=label,bg=CARD,fg=TEXT).pack(anchor='w',padx=45,pady=(7,2)); w.pack(fill='x',padx=45)
        msg=tk.Label(d,text='',bg=CARD,fg=RED); msg.pack(pady=5)
        def save():
            if len(p1.get())<8: msg.config(text='Password must be at least 8 characters.'); return
            if p1.get()!=p2.get(): msg.config(text='Passwords do not match.'); return
            salt,digest=hash_password(p1.get())
            with connect() as con:con.execute('UPDATE users SET password_salt=?,password_hash=?,must_change_password=0,modified=? WHERE id=?',(salt,digest,now(),user_id))
            audit(username,'user',user_id,'PASSWORD_CHANGE','Password changed'); result['ok']=True; d.destroy()
        tk.Button(d,text='Save Password',command=save,bg=BLUE,fg='white',bd=0,padx=18,pady=7).pack(pady=8)
        d.protocol('WM_DELETE_WINDOW',lambda:d.destroy()); d.grab_set(); p1.focus_set(); self.wait_window(d); return result['ok']

    def logout(self):
        if not messagebox.askyesno('Sign out','Sign out of SERVIX?'): return
        audit(self.current_user['username'],'session',self.current_user['id'],'LOGOUT','User signed out')
        for w in self.winfo_children(): w.destroy()
        self.current_user=None; self.withdraw()
        if self.login(): self.deiconify(); self.build_shell(); self.show_dashboard()
        else:self.destroy()

    def set_initial_password(self,user_id):
        result={'ok':False}; d=tk.Toplevel(self); d.title('Create Administrator Password'); d.geometry('430x310'); d.resizable(False,False); d.configure(bg=CARD)
        tk.Label(d,text='Secure Administrator Account',bg=CARD,fg=NAVY,font=('Segoe UI',14,'bold')).pack(pady=(22,5))
        tk.Label(d,text='Create the first SERVIX administrator password.\nNo default password is stored in the application.',bg=CARD,fg=MUTED,justify='center').pack(pady=(0,12))
        tk.Label(d,text='New Password (minimum 8 characters)',bg=CARD,fg=TEXT).pack(anchor='w',padx=45); p1=ttk.Entry(d,show='*'); p1.pack(fill='x',padx=45,pady=(3,9))
        tk.Label(d,text='Confirm Password',bg=CARD,fg=TEXT).pack(anchor='w',padx=45); p2=ttk.Entry(d,show='*'); p2.pack(fill='x',padx=45,pady=(3,8))
        msg=tk.Label(d,text='',bg=CARD,fg=RED); msg.pack()
        def save():
            if len(p1.get())<8: msg.config(text='Password must be at least 8 characters.'); return
            if p1.get()!=p2.get(): msg.config(text='Passwords do not match.'); return
            salt,digest=hash_password(p1.get())
            with connect() as con: con.execute('UPDATE users SET password_salt=?,password_hash=?,must_change_password=0,modified=? WHERE id=?',(salt,digest,now(),user_id))
            result['ok']=True; d.destroy()
        tk.Button(d,text='Create Password',command=save,bg=BLUE,fg='white',bd=0,padx=20,pady=7).pack(pady=10)
        d.grab_set(); p1.focus_set(); self.wait_window(d); return result['ok']

    def permitted(self,permission):
        return bool(self.current_user and can(self.current_user['role'],permission))

    def require(self,permission):
        if self.permitted(permission): return True
        messagebox.showwarning('Access restricted','Your SERVIX role does not have permission for this area.')
        return False

    def can_edit(self):
        return bool(self.current_user and self.current_user['role'] != 'Management / View Only')

    def require_edit(self):
        if self.can_edit(): return True
        messagebox.showwarning('View only','Management / View Only can review SERVIX records but cannot create, edit, delete, return, upload or otherwise modify data.')
        return False

    def build_shell(self):
        self.sidebar=tk.Frame(self,bg='#063765',width=168); self.sidebar.pack(side='left',fill='y'); self.sidebar.pack_propagate(False)
        brand=tk.Frame(self.sidebar,bg='#073A69',height=62); brand.pack(fill='x'); brand.pack_propagate(False)
        logo_path=get_setting('company_logo_path','')
        self.brand_image=None
        if logo_path and Path(logo_path).exists():
            try:
                self.brand_image=tk.PhotoImage(file=logo_path)
                tk.Label(brand,image=self.brand_image,bg='#073A69').pack(anchor='w',padx=18,pady=(4,0))
            except tk.TclError: tk.Label(brand,text=get_setting('company_short_name','HAC'),font=('Segoe UI',25,'bold'),bg='#073A69',fg='white').pack(anchor='w',padx=20,pady=(5,0))
        else: tk.Label(brand,text=get_setting('company_short_name','HAC'),font=('Segoe UI',25,'bold'),bg='#073A69',fg='white').pack(anchor='w',padx=20,pady=(5,0))
        tk.Label(brand,text='SERVICE MANAGEMENT',font=('Segoe UI',6,'bold'),bg='#073A69',fg='#B9D9F4').pack(anchor='w',padx=21)
        self.nav={}
        items=[('Dashboard','⌂',self.show_dashboard,'dashboard'),('Service Calls','⌕',self.show_services,'services'),('Clients','♟',self.show_clients,'clients'),('Equipment','▣',self.show_equipment,'equipment'),('Warranty & AMC','◆',self.show_warranty,'warranty'),('Engineers','♟',self.show_engineers,'engineers'),('Parts / Inventory','↕',self.show_parts_inventory,'parts'),('Commercial & Payments','₹',self.show_commercial,'commercial'),('Documents','▧',self.show_documents,'documents'),('Reports & Analytics','▥',self.show_reports,'reports'),('Data Export / Import','⇄',self.show_data_management,'data'),('Administration','⚙',self.show_settings,'admin')]
        items=[x for x in items if self.permitted(x[3])]
        for label,icon,cmd,_perm in items:
            btn=tk.Button(self.sidebar,text=f'  {icon}   {label}',font=('Segoe UI',8),anchor='w',bd=0,relief='flat',bg='#063765',fg='white',activebackground='#0876D1',activeforeground='white',cursor='hand2',command=lambda l=label,c=cmd:self.go(l,c)); btn.pack(fill='x',pady=0,ipady=7); self.nav[label]=btn
        right=tk.Frame(self,bg=BG); right.pack(side='left',fill='both',expand=True)
        top=tk.Frame(right,bg='#063765',height=53); top.pack(fill='x'); top.pack_propagate(False)
        title=tk.Frame(top,bg='#063765'); title.pack(side='left',padx=(18,24),pady=5)
        tk.Label(title,text=get_setting('system_title','Service Management System'),font=('Segoe UI',12,'bold'),bg='#063765',fg='white').pack(anchor='w')
        tk.Label(title,text=get_setting('system_subtitle','Service   |   Calibration   |   Warranty   |   AMC'),font=('Segoe UI',7),bg='#063765',fg='#D6E8F7').pack(anchor='w')
        searchwrap=tk.Frame(top,bg='white'); searchwrap.pack(side='left',fill='x',expand=True,pady=10)
        self.search=tk.Entry(searchwrap,font=('Segoe UI',9),bd=0,bg='white',fg=MUTED,insertbackground=TEXT); self.search.insert(0,'Search by Service ID, Client, Email, Mobile, Serial No., Equipment ID...'); self.search.pack(side='left',fill='x',expand=True,padx=12,ipady=5); self.search.bind('<Return>',lambda e:self.global_search())
        tk.Button(searchwrap,text='⌕',command=self.global_search,bg='#EEF3F8',fg=NAVY,bd=0,font=('Segoe UI',11),padx=12).pack(side='right',fill='y')
        user=tk.Frame(top,bg='#063765'); user.pack(side='right',padx=20)
        tk.Label(user,text='●',bg='#063765',fg='#8BC8F5',font=('Segoe UI',16)).pack(side='left',padx=6)
        uf=tk.Frame(user,bg='#063765'); uf.pack(side='left'); tk.Label(uf,text=self.current_user['display_name'],bg='#063765',fg='white',font=('Segoe UI',8,'bold')).pack(anchor='w'); tk.Label(uf,text=self.current_user['role'],bg='#063765',fg='#D6E8F7',font=('Segoe UI',6)).pack(anchor='w'); tk.Button(user,text='Sign Out',command=self.logout,bg='#063765',fg='white',activebackground='#164F7C',activeforeground='white',bd=0,font=('Segoe UI',7,'underline')).pack(side='left',padx=(10,0))
        self.content=tk.Frame(right,bg=BG); self.content.pack(fill='both',expand=True)

    def go(self,label,cmd):
        for k,b in self.nav.items(): b.configure(bg=NAVY2 if k==label else NAVY,fg='white' if k==label else '#DDE9F7')
        cmd()
    def clear(self):
        for w in self.content.winfo_children(): w.destroy()
    def heading(self,title,subtitle='',action=None,action_text=''):
        h=tk.Frame(self.content,bg=BG); h.pack(fill='x',padx=28,pady=(24,14)); left=tk.Frame(h,bg=BG); left.pack(side='left'); tk.Label(left,text=title,font=('Segoe UI',22,'bold'),bg=BG,fg=TEXT).pack(anchor='w');
        if subtitle: tk.Label(left,text=subtitle,font=('Segoe UI',9),bg=BG,fg=MUTED).pack(anchor='w',pady=(3,0))
        if action: tk.Button(h,text=action_text,command=action,bg=BLUE,fg='white',font=('Segoe UI',9,'bold'),bd=0,padx=18,pady=10,cursor='hand2').pack(side='right')
    def card(self,parent):
        return tk.Frame(parent,bg=CARD,highlightthickness=1,highlightbackground=BORDER)
    def metric(self,parent,title,value,accent=BLUE,sub=''):
        c=self.card(parent); c.pack(side='left',fill='both',expand=True,padx=6); tk.Frame(c,bg=accent,height=4).pack(fill='x'); tk.Label(c,text=title,bg=CARD,fg=MUTED,font=('Segoe UI',9)).pack(anchor='w',padx=16,pady=(13,2)); tk.Label(c,text=str(value),bg=CARD,fg=TEXT,font=('Segoe UI',25,'bold')).pack(anchor='w',padx=16); tk.Label(c,text=sub or ' ',bg=CARD,fg=MUTED,font=('Segoe UI',8)).pack(anchor='w',padx=16,pady=(2,12)); return c
    def q1(self,sql,args=()):
        with connect() as con:return con.execute(sql,args).fetchone()[0]

    def _register_screen(self,title,subtitle,metrics,cols,widths,sql,search_hint,open_col=0,open_fn=None):
        self.clear(); h=tk.Frame(self.content,bg='#164F7C',height=38); h.pack(fill='x'); h.pack_propagate(False)
        tk.Label(h,text=title,bg='#164F7C',fg='white',font=('Segoe UI',10,'bold')).pack(side='left',padx=14)
        tk.Label(h,text=subtitle,bg='#164F7C',fg='#DCECF8',font=('Segoe UI',7)).pack(side='left',padx=8)
        body=tk.Frame(self.content,bg=BG); body.pack(fill='both',expand=True,padx=10,pady=8)
        m=tk.Frame(body,bg=BG); m.pack(fill='x',pady=(0,6))
        for a,b,color,note in metrics:self.metric(m,a,b,color,note)
        bar=tk.Frame(body,bg=CARD,highlightthickness=1,highlightbackground=BORDER); bar.pack(fill='x',pady=(0,6))
        tk.Label(bar,text=title+' Register',bg=CARD,fg=TEXT,font=('Segoe UI',8,'bold')).pack(side='left',padx=(10,8),pady=8)
        q=tk.StringVar(); ttk.Entry(bar,textvariable=q,width=30).pack(side='left',pady=6)
        tk.Label(bar,text=search_hint,bg=CARD,fg=MUTED,font=('Segoe UI',7)).pack(side='left',padx=8)
        card=self.card(body); card.pack(fill='both',expand=True); tr=ttk.Treeview(card,columns=cols,show='headings')
        for x,w in zip(cols,widths):tr.heading(x,text=x); tr.column(x,width=w,minwidth=65,anchor='w')
        tr.pack(fill='both',expand=True,padx=7,pady=7)
        def load(*_):
            for x in tr.get_children():tr.delete(x)
            term=q.get().strip().lower()
            with connect() as con: rows=con.execute(sql).fetchall()
            for r in rows:
                vals=tuple(r)
                if term and term not in ' '.join(str(v or '') for v in vals).lower():continue
                tr.insert('','end',values=vals)
        q.trace_add('write',load); load()
        if open_fn:tr.bind('<Double-1>',lambda e:open_fn(tr.item(tr.focus(),'values')[open_col]) if tr.focus() else None)

    def show_engineers(self):
        self.clear(); h=tk.Frame(self.content,bg='#164F7C',height=38); h.pack(fill='x'); h.pack_propagate(False)
        tk.Label(h,text='Engineers',bg='#164F7C',fg='white',font=('Segoe UI',10,'bold')).pack(side='left',padx=14)
        tk.Label(h,text='Engineer Master / Workload / Assignment',bg='#164F7C',fg='#DCECF8',font=('Segoe UI',7)).pack(side='left',padx=8)
        body=tk.Frame(self.content,bg=BG); body.pack(fill='both',expand=True,padx=10,pady=8)
        m=tk.Frame(body,bg=BG); m.pack(fill='x',pady=(0,6))
        for x in [('Active Engineers',self.q1("SELECT COUNT(*) FROM engineers WHERE active=1"),GREEN,'Available master records'),('Active Services',self.q1("SELECT COUNT(*) FROM services WHERE engineer!='' AND status NOT IN ('Closed','Cancelled')"),BLUE,'Assigned work'),('Unassigned',self.q1("SELECT COUNT(*) FROM services WHERE (engineer IS NULL OR engineer='') AND status NOT IN ('Closed','Cancelled')"),ORANGE,'Needs assignment'),('Closed Jobs',self.q1("SELECT COUNT(*) FROM services WHERE engineer!='' AND status='Closed'"),GREEN,'Completed')]: self.metric(m,*x)
        bar=self.card(body); bar.pack(fill='x',pady=(0,6)); q=tk.StringVar(); ttk.Entry(bar,textvariable=q,width=30).pack(side='left',padx=10,pady=7)
        card=self.card(body); card.pack(fill='both',expand=True); cols=('Code','Engineer','Mobile','Email','Specialization','Active Jobs','Closed Jobs','Status'); tr=ttk.Treeview(card,columns=cols,show='headings')
        for c,w in zip(cols,(90,180,120,190,170,90,90,90)): tr.heading(c,text=c); tr.column(c,width=w,anchor='w')
        tr.pack(fill='both',expand=True,padx=7,pady=7)
        def load(*_):
            tr.delete(*tr.get_children()); term=q.get().strip().lower()
            with connect() as con: rows=con.execute("""SELECT e.id,e.code,e.name,e.mobile,e.email,e.specialization,
              SUM(CASE WHEN s.status NOT IN ('Closed','Cancelled') THEN 1 ELSE 0 END) active_jobs,
              SUM(CASE WHEN s.status='Closed' THEN 1 ELSE 0 END) closed_jobs,e.active
              FROM engineers e LEFT JOIN services s ON lower(trim(s.engineer))=lower(trim(e.name))
              GROUP BY e.id ORDER BY e.active DESC,e.name""").fetchall()
            for r in rows:
                vals=(r['code'],r['name'],r['mobile'],r['email'],r['specialization'],r['active_jobs'],r['closed_jobs'],'Active' if r['active'] else 'Disabled')
                if not term or term in ' '.join(str(v or '') for v in vals).lower(): tr.insert('', 'end',iid=str(r['id']),values=vals)
        q.trace_add('write',load)
        def edit(uid=None):
            if not self.require_edit(): return
            row=None
            if uid:
                with connect() as con: row=con.execute('SELECT * FROM engineers WHERE id=?',(uid,)).fetchone()
            d=tk.Toplevel(self); d.title('Engineer Master'); d.geometry('500x510'); d.configure(bg=CARD); d.transient(self); d.grab_set(); vals={}
            for key,label in [('name','Engineer Name *'),('mobile','Mobile'),('email','Email'),('specialization','Specialization'),('notes','Notes')]:
                tk.Label(d,text=label,bg=CARD,fg=TEXT,font=('Segoe UI',8,'bold')).pack(anchor='w',padx=24,pady=(9,2)); vals[key]=ttk.Entry(d); vals[key].pack(fill='x',padx=24)
                if row: vals[key].insert(0,row[key] or '')
            active=tk.BooleanVar(value=bool(row['active']) if row else True); tk.Checkbutton(d,text='Active engineer',variable=active,bg=CARD).pack(anchor='w',padx=20,pady=10)
            def save():
                name=vals['name'].get().strip()
                if not name:return messagebox.showwarning('Required','Engineer Name is required.',parent=d)
                ts=now()
                with connect() as con:
                    if row: con.execute('UPDATE engineers SET name=?,mobile=?,email=?,specialization=?,active=?,notes=?,modified=? WHERE id=?',(name,vals['mobile'].get().strip(),vals['email'].get().strip(),vals['specialization'].get().strip(),1 if active.get() else 0,vals['notes'].get().strip(),ts,uid))
                    else:
                        n=con.execute('SELECT COALESCE(MAX(id),0)+1 FROM engineers').fetchone()[0]; code=f"ENG-{n:04d}"
                        con.execute('INSERT INTO engineers(code,name,mobile,email,specialization,active,notes,created,modified) VALUES(?,?,?,?,?,?,?,?,?)',(code,name,vals['mobile'].get().strip(),vals['email'].get().strip(),vals['specialization'].get().strip(),1 if active.get() else 0,vals['notes'].get().strip(),ts,ts))
                audit(self.current_user['username'],'engineer',name,'UPDATE' if row else 'CREATE','Engineer master saved'); d.destroy(); load()
            tk.Button(d,text='Save Engineer',command=save,bg=BLUE,fg='white',bd=0,padx=16,pady=7).pack(pady=14)
        tk.Button(bar,text='+ New Engineer',command=lambda:edit(),bg=BLUE,fg='white',bd=0,padx=12,pady=6).pack(side='left',padx=4)
        tk.Button(bar,text='Edit Selected',command=lambda:edit(int(tr.selection()[0])) if tr.selection() else None,bg='#EAF2FF',fg=BLUE,bd=0,padx=12,pady=6).pack(side='left',padx=4)
        load()

    def show_parts_inventory(self):
        self.clear(); h=tk.Frame(self.content,bg='#164F7C',height=38); h.pack(fill='x'); h.pack_propagate(False)
        tk.Label(h,text='Parts / Inventory',bg='#164F7C',fg='white',font=('Segoe UI',10,'bold')).pack(side='left',padx=14)
        tk.Label(h,text='Parts Master / Stock Ledger / Service Usage',bg='#164F7C',fg='#DCECF8',font=('Segoe UI',7)).pack(side='left',padx=8)
        body=tk.Frame(self.content,bg=BG); body.pack(fill='both',expand=True,padx=10,pady=8)
        m=tk.Frame(body,bg=BG); m.pack(fill='x',pady=(0,6))
        stock_sql="SELECT COALESCE(SUM(CASE WHEN movement_type IN ('Opening','Receipt','Adjustment +','Return') THEN qty ELSE -qty END),0) FROM inventory_movements"
        for x in [('Part Masters',self.q1('SELECT COUNT(*) FROM inventory_items WHERE active=1'),BLUE,'Active items'),('Stock On Hand',self.q1(stock_sql),GREEN,'All units'),('Service Part Entries',self.q1('SELECT COUNT(*) FROM parts'),ORANGE,'Historical usage'),('Low Stock',self.q1("""SELECT COUNT(*) FROM inventory_items i WHERE active=1 AND (SELECT COALESCE(SUM(CASE WHEN m.movement_type IN ('Opening','Receipt','Adjustment +','Return') THEN m.qty ELSE -m.qty END),0) FROM inventory_movements m WHERE m.item_id=i.id)<=i.reorder_level"""),RED,'At/below reorder level')]: self.metric(m,*x)
        bar=self.card(body); bar.pack(fill='x',pady=(0,6)); q=tk.StringVar(); ttk.Entry(bar,textvariable=q,width=28).pack(side='left',padx=10,pady=7)
        cols=('Code','Part Name','Part No.','Category','Unit','Stock','Reorder','Status'); card=self.card(body); card.pack(fill='both',expand=True); tr=ttk.Treeview(card,columns=cols,show='headings')
        for c,w in zip(cols,(90,230,130,140,70,80,80,90)): tr.heading(c,text=c); tr.column(c,width=w,anchor='w')
        tr.pack(fill='both',expand=True,padx=7,pady=7)
        def load(*_):
            tr.delete(*tr.get_children()); term=q.get().strip().lower()
            with connect() as con: rows=con.execute("""SELECT i.*,COALESCE(SUM(CASE WHEN m.movement_type IN ('Opening','Receipt','Adjustment +','Return') THEN m.qty ELSE -m.qty END),0) stock FROM inventory_items i LEFT JOIN inventory_movements m ON m.item_id=i.id GROUP BY i.id ORDER BY i.active DESC,i.part_name""").fetchall()
            for r in rows:
                vals=(r['code'],r['part_name'],r['part_number'],r['category'],r['unit'],r['stock'],r['reorder_level'],'Active' if r['active'] else 'Disabled')
                if not term or term in ' '.join(str(v or '') for v in vals).lower():tr.insert('','end',iid=str(r['id']),values=vals)
        q.trace_add('write',load)
        def edit(uid=None):
            if not self.require_edit(): return
            row=None
            if uid:
                with connect() as con: row=con.execute('SELECT * FROM inventory_items WHERE id=?',(uid,)).fetchone()
            d=tk.Toplevel(self); d.title('Part Master'); d.geometry('500x540'); d.configure(bg=CARD); d.transient(self); d.grab_set(); vals={}
            for key,label in [('part_name','Part Name *'),('part_number','Part Number'),('category','Category'),('unit','Unit'),('reorder_level','Reorder Level'),('notes','Notes')]:
                tk.Label(d,text=label,bg=CARD,fg=TEXT,font=('Segoe UI',8,'bold')).pack(anchor='w',padx=24,pady=(8,2)); vals[key]=ttk.Entry(d); vals[key].pack(fill='x',padx=24)
                if row:vals[key].insert(0,str(row[key] or ''))
            if not row: vals['unit'].insert(0,'Nos'); vals['reorder_level'].insert(0,'0')
            active=tk.BooleanVar(value=bool(row['active']) if row else True); tk.Checkbutton(d,text='Active part',variable=active,bg=CARD).pack(anchor='w',padx=20,pady=8)
            def save():
                name=vals['part_name'].get().strip()
                if not name:return messagebox.showwarning('Required','Part Name is required.',parent=d)
                try: reorder=float(vals['reorder_level'].get() or 0)
                except ValueError:return messagebox.showwarning('Invalid','Reorder Level must be numeric.',parent=d)
                ts=now()
                with connect() as con:
                    if row:con.execute('UPDATE inventory_items SET part_name=?,part_number=?,category=?,unit=?,reorder_level=?,active=?,notes=?,modified=? WHERE id=?',(name,vals['part_number'].get().strip(),vals['category'].get().strip(),vals['unit'].get().strip() or 'Nos',reorder,1 if active.get() else 0,vals['notes'].get().strip(),ts,uid))
                    else:
                        n=con.execute('SELECT COALESCE(MAX(id),0)+1 FROM inventory_items').fetchone()[0]; code=f"PRT-{n:05d}"
                        con.execute('INSERT INTO inventory_items(code,part_name,part_number,category,unit,reorder_level,active,notes,created,modified) VALUES(?,?,?,?,?,?,?,?,?,?)',(code,name,vals['part_number'].get().strip(),vals['category'].get().strip(),vals['unit'].get().strip() or 'Nos',reorder,1 if active.get() else 0,vals['notes'].get().strip(),ts,ts))
                audit(self.current_user['username'],'inventory',name,'UPDATE' if row else 'CREATE','Part master saved'); d.destroy(); load()
            tk.Button(d,text='Save Part',command=save,bg=BLUE,fg='white',bd=0,padx=16,pady=7).pack(pady=14)
        def movement():
            if not self.require_edit(): return
            if not tr.selection():return messagebox.showwarning('Inventory','Select a part first.')
            uid=int(tr.selection()[0]); name=tr.item(tr.selection()[0],'values')[1]
            d=tk.Toplevel(self); d.title('Stock Movement'); d.geometry('440x370'); d.configure(bg=CARD); d.transient(self); d.grab_set()
            tk.Label(d,text=name,bg=CARD,fg=NAVY,font=('Segoe UI',12,'bold')).pack(pady=(18,10)); typ=ttk.Combobox(d,state='readonly',values=['Opening','Receipt','Issue','Return','Adjustment +','Adjustment -']); typ.set('Receipt'); typ.pack(fill='x',padx=28,pady=5)
            qty=ttk.Entry(d); qty.pack(fill='x',padx=28,pady=5); qty.insert(0,'1'); ref=ttk.Entry(d); ref.pack(fill='x',padx=28,pady=5); ref.insert(0,'Reference / supplier / note')
            def save():
                try:v=float(qty.get())
                except ValueError:return messagebox.showwarning('Invalid','Quantity must be numeric.',parent=d)
                if v<=0:return messagebox.showwarning('Invalid','Quantity must be greater than zero.',parent=d)
                with connect() as con:
                    con.execute('INSERT INTO inventory_movements(item_id,movement_date,movement_type,qty,reference,notes,username) VALUES(?,?,?,?,?,?,?)',(uid,now(),typ.get(),v,ref.get().strip(),'Manual stock movement',self.current_user['username']))
                audit(self.current_user['username'],'inventory',uid,'STOCK '+typ.get(),str(v)); d.destroy(); load()
            tk.Button(d,text='Post Movement',command=save,bg=GREEN,fg='white',bd=0,padx=16,pady=7).pack(pady=18)
        tk.Button(bar,text='+ New Part',command=lambda:edit(),bg=BLUE,fg='white',bd=0,padx=12,pady=6).pack(side='left',padx=4)
        tk.Button(bar,text='Edit Selected',command=lambda:edit(int(tr.selection()[0])) if tr.selection() else None,bg='#EAF2FF',fg=BLUE,bd=0,padx=12,pady=6).pack(side='left',padx=4)
        tk.Button(bar,text='Stock Movement',command=movement,bg=GREEN,fg='white',bd=0,padx=12,pady=6).pack(side='left',padx=4)
        load()

    def show_documents(self):
        self.clear(); h=tk.Frame(self.content,bg='#164F7C',height=38); h.pack(fill='x'); h.pack_propagate(False)
        tk.Label(h,text='Documents',bg='#164F7C',fg='white',font=('Segoe UI',10,'bold')).pack(side='left',padx=14)
        tk.Label(h,text='Service Documents / Photos / Certificates',bg='#164F7C',fg='#DCECF8',font=('Segoe UI',7)).pack(side='left',padx=8)
        body=tk.Frame(self.content,bg=BG); body.pack(fill='both',expand=True,padx=10,pady=8)
        m=tk.Frame(body,bg=BG); m.pack(fill='x',pady=(0,6))
        for x in [('Attachments',self.q1('SELECT COUNT(*) FROM attachments'),BLUE,'Images and PDFs'),('PDF Files',self.q1("SELECT COUNT(*) FROM attachments WHERE lower(original_name) LIKE '%.pdf'"),RED,'Stored PDFs'),('Photos',self.q1("SELECT COUNT(*) FROM attachments WHERE lower(original_name) NOT LIKE '%.pdf'"),GREEN,'Stored images'),('Services With Files',self.q1('SELECT COUNT(DISTINCT service_id) FROM attachments'),ORANGE,'Documented jobs')]: self.metric(m,*x)
        bar=self.card(body); bar.pack(fill='x',pady=(0,6)); q=tk.StringVar(); ttk.Entry(bar,textvariable=q,width=30).pack(side='left',padx=10,pady=7)
        kind=ttk.Combobox(bar,state='readonly',values=['All','PDF','Image'],width=12); kind.set('All'); kind.pack(side='left',padx=4)
        card=self.card(body); card.pack(fill='both',expand=True); cols=('Service ID','Client','Equipment','File Name','Type','Size KB','Added'); tr=ttk.Treeview(card,columns=cols,show='headings')
        for c,w in zip(cols,(110,190,110,300,80,80,150)):tr.heading(c,text=c);tr.column(c,width=w,anchor='w')
        tr.pack(fill='both',expand=True,padx=7,pady=7)
        def load(*_):
            tr.delete(*tr.get_children()); term=q.get().strip().lower(); k=kind.get()
            with connect() as con: rows=con.execute("""SELECT a.id,s.code service_code,c.name,e.code equipment,a.original_name,a.stored_path,a.kind,a.stored_size,a.created
              FROM attachments a JOIN services s ON s.id=a.service_id LEFT JOIN clients c ON c.id=s.client_id LEFT JOIN equipment e ON e.id=s.equipment_id ORDER BY a.id DESC""").fetchall()
            for r in rows:
                typ='PDF' if (r['original_name'] or '').lower().endswith('.pdf') else 'Image'
                vals=(r['service_code'],r['name'],r['equipment'],r['original_name'],typ,round((r['stored_size'] or 0)/1024,1),r['created'])
                if k!='All' and typ!=k:continue
                if not term or term in ' '.join(str(v or '') for v in vals).lower():tr.insert('','end',iid=str(r['id']),values=vals)
        q.trace_add('write',load); kind.bind('<<ComboboxSelected>>',load)
        def selected_row():
            if not tr.selection(): messagebox.showwarning('Documents','Select a document first.'); return None
            with connect() as con:return con.execute('SELECT * FROM attachments WHERE id=?',(int(tr.selection()[0]),)).fetchone()
        def open_file():
            r=selected_row()
            if not r:return
            p=Path(r['stored_path'])
            if not p.is_absolute():p=DATA_ROOT/p
            if not p.exists():return messagebox.showerror('Document missing','The stored file could not be found:\n'+str(p))
            try: os.startfile(str(p))
            except Exception as ex:messagebox.showerror('Open Document',str(ex))
        def folder():
            r=selected_row()
            if not r:return
            p=Path(r['stored_path']); p=p if p.is_absolute() else DATA_ROOT/p
            if not p.exists():return messagebox.showerror('Document missing','The stored file could not be found.')
            try: os.startfile(str(p.parent))
            except Exception as ex:messagebox.showerror('Open Folder',str(ex))
        def service():
            if tr.selection():self.show_service_detail(tr.item(tr.selection()[0],'values')[0])
        def remove():
            if not self.require_edit(): return
            r=selected_row()
            if not r:return
            if not messagebox.askyesno('Remove document','Remove this attachment from SERVIX?\n\nThe stored file will also be deleted when possible.'):return
            p=Path(r['stored_path']); p=p if p.is_absolute() else DATA_ROOT/p
            with connect() as con:con.execute('DELETE FROM attachments WHERE id=?',(r['id'],))
            try:
                if p.exists():p.unlink()
            except OSError:pass
            audit(self.current_user['username'],'attachment',r['id'],'DELETE',r['original_name'] or '');load()
        tk.Button(bar,text='Open File',command=open_file,bg=BLUE,fg='white',bd=0,padx=12,pady=6).pack(side='left',padx=4)
        tk.Button(bar,text='Open Folder',command=folder,bg='#EAF2FF',fg=BLUE,bd=0,padx=12,pady=6).pack(side='left',padx=4)
        tk.Button(bar,text='Open Service',command=service,bg='#EAF2FF',fg=BLUE,bd=0,padx=12,pady=6).pack(side='left',padx=4)
        tk.Button(bar,text='Remove',command=remove,bg='#FDECEC',fg=RED,bd=0,padx=12,pady=6).pack(side='left',padx=4)
        tr.bind('<Double-1>',lambda e:open_file());load()

    def show_dashboard(self):
        self.clear()
        kpi=tk.Frame(self.content,bg=BG); kpi.pack(fill='x',padx=10,pady=(10,7))
        data=[
            ('Open Calls',self.q1("SELECT COUNT(*) FROM services WHERE status NOT IN ('Closed','Cancelled')"),'#83BCF4',''),
            ('Overdue',self.q1("SELECT COUNT(*) FROM services WHERE status NOT IN ('Closed','Cancelled') AND date(opened)<date('now','-7 day')"),'#FF999B',''),
            ('Awaiting Parts',self.q1("SELECT COUNT(*) FROM services WHERE status='Awaiting Parts'"),'#FFD65F',''),
            ('Awaiting Customer',self.q1("SELECT COUNT(*) FROM services WHERE status='Awaiting Customer'"),'#B892EF',''),
            ('Quotation Pending',self.q1("SELECT COUNT(*) FROM services WHERE quote_status='Pending Decision'"),'#58D1C9',''),
            ('Payment Pending',self.q1("SELECT COUNT(*) FROM services WHERE payment_status IN ('Pending','Part Paid','Invoice Raised','To Be Invoiced')"),'#FFAD73','₹ {:,.0f}'.format(self.q1("SELECT COALESCE(SUM(MAX(0,COALESCE(invoice_amount,0)-COALESCE(amount_received,0))),0) FROM services"))),
            ('Calibration Due',self.q1("SELECT COUNT(*) FROM calibration WHERE next_due!='' AND date(next_due)<=date('now','+30 day')"),'#CBD4DE','(30 days)'),
            ('AMC Expiring',self.q1("SELECT COUNT(*) FROM equipment WHERE amc_till!='' AND date(amc_till)>=date('now') AND date(amc_till)<=date('now','+60 day')"),'#A9E8B1','(60 days)')]
        for title,val,color,sub in data:
            card=tk.Frame(kpi,bg=color,highlightthickness=1,highlightbackground='#D5DFE9'); card.pack(side='left',fill='both',expand=True,padx=4)
            tk.Label(card,text=str(val),bg=color,fg='#071426',font=('Segoe UI',17,'bold')).pack(pady=(8,0))
            tk.Label(card,text=title,bg=color,fg='#071426',font=('Segoe UI',8,'bold')).pack()
            tk.Label(card,text=sub or ' ',bg=color,fg='#071426',font=('Segoe UI',7,'bold')).pack(pady=(0,7))

        analytics=tk.Frame(self.content,bg=BG); analytics.pack(fill='x',padx=10,pady=(0,7))
        def panel(parent,title):
            f=self.card(parent); f.pack(side='left',fill='both',expand=True,padx=4); tk.Label(f,text=title,bg=CARD,fg=TEXT,font=('Segoe UI',9,'bold')).pack(anchor='w',padx=10,pady=(7,3)); return f
        p1=panel(analytics,'Service Calls by Month'); p2=panel(analytics,'Service Type (Current Year)'); p3=panel(analytics,'FOC vs Chargeable'); p4=panel(analytics,'Payment Status (Chargeable)'); p5=panel(analytics,'Top 5 Customers (Service Calls)')
        months=['Jan','Feb','Mar','Apr','May','Jun','Jul','Aug','Sep','Oct','Nov','Dec']; canvas=tk.Canvas(p1,height=105,bg='white',highlightthickness=0); canvas.pack(fill='x',padx=8,pady=3)
        with connect() as con: monthly={int(r[0]):r[1] for r in con.execute("SELECT CAST(strftime('%m',opened) AS INTEGER),COUNT(*) FROM services WHERE strftime('%Y',opened)=strftime('%Y','now') GROUP BY 1")}
        mx=max([1]+list(monthly.values()))
        for i,m in enumerate(months):
            x=10+i*22; h=55*monthly.get(i+1,0)/mx; canvas.create_rectangle(x,75-h,x+12,75,fill='#4B9BE8',outline=''); canvas.create_text(x+6,88,text=m,font=('Segoe UI',6),fill=MUTED)
        def statlines(parent,rows):
            for label,val,color in rows:
                r=tk.Frame(parent,bg=CARD); r.pack(fill='x',padx=10,pady=3); tk.Label(r,text='■',fg=color,bg=CARD,font=('Segoe UI',8)).pack(side='left'); tk.Label(r,text=label,bg=CARD,fg=TEXT,font=('Segoe UI',7)).pack(side='left',padx=4); tk.Label(r,text=str(val),bg=CARD,fg=TEXT,font=('Segoe UI',7,'bold')).pack(side='right')
        statlines(p2,[('Breakdown',self.q1("SELECT COUNT(*) FROM services WHERE reason='Breakdown / Complaint'"),'#FF4545'),('Calibration',self.q1("SELECT COUNT(*) FROM services WHERE reason='Calibration'"),BLUE),('Preventive PM',self.q1("SELECT COUNT(*) FROM services WHERE reason LIKE '%Preventive%'"),GREEN),('Others',self.q1("SELECT COUNT(*) FROM services WHERE reason NOT IN ('Breakdown / Complaint','Calibration','Preventive Maintenance')"),ORANGE)])
        statlines(p3,[('Chargeable',self.q1("SELECT COUNT(*) FROM services WHERE foc_chargeable='Chargeable'"),BLUE),('FOC / Warranty / AMC',self.q1("SELECT COUNT(*) FROM services WHERE foc_chargeable='FOC' OR warranty='Yes' OR amc='Yes'"),GREEN)])
        statlines(p4,[('Paid',self.q1("SELECT COUNT(*) FROM services WHERE payment_status='Paid'"),GREEN),('Pending',self.q1("SELECT COUNT(*) FROM services WHERE payment_status IN ('Pending','Part Paid')"),ORANGE),('Not Invoiced',self.q1("SELECT COUNT(*) FROM services WHERE payment_status IN ('Not Applicable','To Be Invoiced')"),'#8B9BAD')])
        with connect() as con: tops=con.execute("SELECT c.name,COUNT(*) n FROM services s JOIN clients c ON c.id=s.client_id GROUP BY c.id ORDER BY n DESC LIMIT 5").fetchall()
        statlines(p5,[(r['name'],r['n'],BLUE) for r in tops] or [('No service data yet',0,BLUE)])

        lower=tk.Frame(self.content,bg=BG); lower.pack(fill='both',expand=True,padx=10,pady=(0,8))
        recent=self.card(lower); recent.pack(side='left',fill='both',expand=True,padx=(4,4))
        rh=tk.Frame(recent,bg=CARD); rh.pack(fill='x',padx=10,pady=(7,3)); tk.Label(rh,text='Recent / Open Service Calls',font=('Segoe UI',9,'bold'),bg=CARD,fg=TEXT).pack(side='left'); tk.Button(rh,text='View All',command=self.show_services,bg=CARD,fg=BLUE,bd=0,font=('Segoe UI',7,'underline')).pack(side='right')
        self.service_tree(recent,5)
        alerts=self.card(lower); alerts.pack(side='left',fill='both',padx=(4,4)); tk.Label(alerts,text='Alerts & Reminders',font=('Segoe UI',9,'bold'),bg=CARD,fg=TEXT).pack(anchor='w',padx=12,pady=(8,5))
        alert_rows=[
            ('●',RED,str(self.q1("SELECT COUNT(*) FROM services WHERE status NOT IN ('Closed','Cancelled') AND date(opened)<date('now','-7 day')"))+' service calls overdue'),
            ('●',ORANGE,str(self.q1("SELECT COUNT(*) FROM calibration WHERE next_due!='' AND date(next_due)<=date('now','+30 day')"))+' calibrations due within 30 days'),
            ('●',ORANGE,str(self.q1("SELECT COUNT(*) FROM equipment WHERE warranty_till!='' AND date(warranty_till)>=date('now') AND date(warranty_till)<=date('now','+30 day')"))+' warranties expiring this month'),
            ('●',ORANGE,str(self.q1("SELECT COUNT(*) FROM equipment WHERE amc_till!='' AND date(amc_till)>=date('now') AND date(amc_till)<=date('now','+60 day')"))+' AMC expiring in 60 days'),
            ('●',ORANGE,str(self.q1("SELECT COUNT(*) FROM services WHERE payment_status IN ('Pending','Part Paid')"))+' invoices pending payment'),
            ('△',RED,str(self.q1("SELECT COUNT(*) FROM equipment WHERE serial IS NULL OR serial=''"))+' equipment with missing serial numbers')
        ]
        for icon,color,msg in alert_rows:
            r=tk.Frame(alerts,bg=CARD); r.pack(fill='x',padx=12,pady=4); tk.Label(r,text=icon,bg=CARD,fg=color,font=('Segoe UI',9,'bold')).pack(side='left'); tk.Label(r,text=msg,bg=CARD,fg=TEXT,font=('Segoe UI',7)).pack(side='left',padx=7)

    def service_tree(self,parent,limit=None,where='',args=()):
        wrap=tk.Frame(parent,bg=CARD); wrap.pack(fill='both',expand=True,padx=14,pady=(0,14)); cols=('Service ID','Opened','Client','SERVIX Equipment','Reason','Engineer','Status','Payment'); tree=ttk.Treeview(wrap,columns=cols,show='headings');
        widths=[115,125,190,135,150,120,140,110]
        for c,w in zip(cols,widths): tree.heading(c,text=c); tree.column(c,width=w,anchor='w')
        tree.pack(side='left',fill='both',expand=True); sb=ttk.Scrollbar(wrap,orient='vertical',command=tree.yview); sb.pack(side='right',fill='y'); tree.configure(yscrollcommand=sb.set)
        sql='''SELECT s.code,s.opened,c.name,e.code,s.reason,COALESCE(s.engineer,''),s.status,COALESCE(s.payment_status,'') FROM services s LEFT JOIN clients c ON c.id=s.client_id LEFT JOIN equipment e ON e.id=s.equipment_id '''
        if where: sql+=' WHERE '+where
        sql+=' ORDER BY s.id DESC'+(f' LIMIT {limit}' if limit else '')
        with connect() as con:
            for r in con.execute(sql,args): tree.insert('','end',values=tuple(r))
        tree.bind('<Double-1>',lambda e:self.open_selected_service(tree)); return tree
    def open_selected_service(self,tree):
        item=tree.focus();
        if item:self.show_service_detail(tree.item(item,'values')[0])

    def show_services(self):
        self.clear(); self.heading('Service Calls','Search, review and update complete service history',self.show_new_service,'+ New Service')
        bar=self.card(self.content); bar.pack(fill='x',padx=28,pady=(0,12)); tk.Label(bar,text='Status',bg=CARD,fg=MUTED).pack(side='left',padx=(15,5),pady=12); st=ttk.Combobox(bar,width=20,state='readonly',values=['All','New','Assigned','Received','Under Diagnosis','Awaiting Customer','Awaiting Approval','Awaiting Parts','Repair in Progress','Testing','Ready for Dispatch','Dispatched','Closed']); st.set('All'); st.pack(side='left'); holder=self.card(self.content); holder.pack(fill='both',expand=True,padx=28,pady=(0,22))
        tree=self.service_tree(holder)
        def filter_it(*_):
            for i in tree.get_children():tree.delete(i)
            where='' if st.get()=='All' else 's.status=?'; args=() if not where else (st.get(),)
            sql='''SELECT s.code,s.opened,c.name,e.code,s.reason,COALESCE(s.engineer,''),s.status,COALESCE(s.payment_status,'') FROM services s LEFT JOIN clients c ON c.id=s.client_id LEFT JOIN equipment e ON e.id=s.equipment_id'''+((' WHERE '+where) if where else '')+' ORDER BY s.id DESC'
            with connect() as con:
                for r in con.execute(sql,args):tree.insert('','end',values=tuple(r))
        st.bind('<<ComboboxSelected>>',filter_it)

    def form_field(self,parent,label,row,col,values=None,width=30,required=False):
        tk.Label(parent,text=label+(' *' if required else ''),bg=CARD,fg=TEXT,font=('Segoe UI',9,'bold')).grid(row=row,column=col,sticky='w',padx=10,pady=(8,3)); w=ttk.Combobox(parent,values=values,width=width,state='readonly') if values is not None else ttk.Entry(parent,width=width); w.grid(row=row+1,column=col,sticky='ew',padx=10,pady=(0,8)); return w

    def show_new_service(self):
        if not self.require_edit(): return self.show_services()
        self.clear()
        bar=tk.Frame(self.content,bg='#164F7C',height=36); bar.pack(fill='x'); bar.pack_propagate(False)
        tk.Label(bar,text='Service Request - New / Edit',bg='#164F7C',fg='white',font=('Segoe UI',10,'bold')).pack(side='left',padx=14)
        tk.Label(bar,text='Service ID:',bg='#164F7C',fg='white',font=('Segoe UI',8)).pack(side='left',padx=(12,6))
        tk.Label(bar,text='AUTO ON SAVE',bg='#FFF8B8',fg=TEXT,font=('Segoe UI',8,'bold'),padx=14,pady=3).pack(side='left')
        tk.Label(bar,text='New Service Request',bg='#164F7C',fg='#DCECF8',font=('Segoe UI',8)).pack(side='right',padx=16)
        workspace=tk.Frame(self.content,bg=BG); workspace.pack(fill='both',expand=True,padx=10,pady=(6,8))
        form=self.card(workspace); form.pack(fill='x'); form.grid_columnconfigure((0,1,2),weight=1)
        section=tk.Frame(form,bg='#F7FAFD',highlightthickness=1,highlightbackground='#B8D8F3'); section.grid(row=0,column=0,columnspan=3,sticky='ew',padx=8,pady=(8,2))
        for i,title in enumerate(('1. Client Information','2. Equipment Information','3. Service Details','4. Calibration Details')):
            section.grid_columnconfigure(i,weight=1)
            tk.Label(section,text=title,bg='#F7FAFD',fg=BLUE,font=('Segoe UI',8,'bold'),anchor='w').grid(row=0,column=i,sticky='ew',padx=10,pady=7)

        client=self.form_field(form,'Client / Search Client',2,0,[],required=True)
        equip=self.form_field(form,'Equipment / Serial / Make / Model',2,1,[],required=True)
        reason=self.form_field(form,'Reason for Service',2,2,['Breakdown / Complaint','Calibration','Preventive Maintenance','AMC Preventive Visit','Installation / Commissioning','Inspection / Check-up','Performance Verification','Software/Firmware Update','Accessory Replacement','Part Replacement','Customer Requested Service','Other'],required=True)
        warranty=self.form_field(form,'Under Warranty?',4,0,['Yes','No'],required=True)
        amc=self.form_field(form,'Under AMC?',4,1,['Yes','No'],required=True)
        engineer=self.form_field(form,'Assigned Engineer (important)',4,2,[])
        priority=self.form_field(form,'Priority',6,0,['Normal','Urgent','Critical']); priority.set('Normal')
        source=self.form_field(form,'Request Source (optional)',6,1,['Phone','Email','WhatsApp','Walk-in','Other'])
        status=self.form_field(form,'Status',6,2,['New','Assigned','Received']); status.set('New')

        info=tk.Frame(form,bg='#F7FAFD',highlightthickness=1,highlightbackground='#D6E6F3'); info.grid(row=7,column=0,columnspan=3,sticky='ew',padx=10,pady=(3,3))
        for i in range(3): info.grid_columnconfigure(i,weight=1)
        tk.Label(info,text='Client: select an existing customer or use + Quick Add Client',bg='#F7FAFD',fg=MUTED,font=('Segoe UI',7),anchor='w').grid(row=0,column=0,sticky='ew',padx=8,pady=5)
        tk.Label(info,text='Equipment: filtered to the selected client; serial identity is preserved',bg='#F7FAFD',fg=MUTED,font=('Segoe UI',7),anchor='w').grid(row=0,column=1,sticky='ew',padx=8,pady=5)
        cal_hint=tk.Label(info,text='Calibration fields become available after the service is created',bg='#F7FAFD',fg=MUTED,font=('Segoe UI',7),anchor='w')
        cal_hint.grid(row=0,column=2,sticky='ew',padx=8,pady=5)

        cmap={}; emap={}
        def refresh_lists(select_client_id=None,select_equipment_id=None):
            nonlocal cmap,emap
            with connect() as con:
                engineer_names=[x['name'] for x in con.execute('SELECT name FROM engineers WHERE active=1 ORDER BY name')]
                clients=[(x['id'],f"{x['code']} — {x['name']}") for x in con.execute('SELECT id,code,name FROM clients ORDER BY name')]
                equipment=[(x['id'],x['client_id'],f"{x['code']} — {x['make']} {x['model']} — {x['serial'] or 'Serial not available'}") for x in con.execute('SELECT id,client_id,code,make,model,serial FROM equipment ORDER BY id DESC')]
            engineer['values']=engineer_names
            cmap={v:k for k,v in clients}
            chosen_client=select_client_id or cmap.get(client.get())
            client['values']=list(cmap)
            if chosen_client:
                for label,cid in cmap.items():
                    if cid==chosen_client: client.set(label); break
            emap={label:eid for eid,cid,label in equipment if not chosen_client or cid==chosen_client}
            equip['values']=list(emap)
            if select_equipment_id:
                for label,eid in emap.items():
                    if eid==select_equipment_id: equip.set(label); break
            elif equip.get() not in emap: equip.set('')

        def on_client(*_):
            refresh_lists()
        client.bind('<<ComboboxSelected>>',on_client)

        quick=tk.Frame(form,bg=CARD); quick.grid(row=8,column=0,columnspan=3,sticky='ew',padx=10,pady=(2,8))
        tk.Label(quick,text='Not in SERVIX yet?',bg=CARD,fg=MUTED,font=('Segoe UI',8)).pack(side='left',padx=(0,10))

        def quick_client():
            d=tk.Toplevel(self); d.title('Quick Add Client'); d.geometry('520x430'); d.configure(bg=CARD); d.transient(self); d.grab_set()
            vals={}
            for key,label in [('name','Client / Company *'),('contact','Contact Person'),('mobile','Mobile'),('email','Email'),('city','City'),('address','Address')]:
                tk.Label(d,text=label,bg=CARD,fg=TEXT,font=('Segoe UI',9,'bold')).pack(anchor='w',padx=24,pady=(8,2)); vals[key]=ttk.Entry(d); vals[key].pack(fill='x',padx=24)
            def save_client():
                name=vals['name'].get().strip(); mobile=vals['mobile'].get().strip(); email=vals['email'].get().strip()
                if not name or (not mobile and not email): return messagebox.showwarning('Required','Client name and at least Mobile or Email are required.',parent=d)
                with connect() as con:
                    dup=con.execute("""SELECT id,code,name FROM clients WHERE
                        (?<>'' AND REPLACE(REPLACE(mobile,' ',''),'-','')=REPLACE(REPLACE(?,' ',''),'-',''))
                        OR (?<>'' AND LOWER(email)=LOWER(?))""",(mobile,mobile,email,email)).fetchone()
                    if dup:
                        if messagebox.askyesno('Existing client found',f"{dup['code']} — {dup['name']} already matches this mobile/email.\n\nUse the existing client?",parent=d):
                            cid=dup['id']; d.destroy(); refresh_lists(select_client_id=cid); return
                        return messagebox.showwarning('Duplicate protected','Create Anyway is intentionally blocked in quick entry. Use the Clients screen for an authorized duplicate override.',parent=d)
                    ts=now(); code=next_code('CLI','clients')
                    cur=con.execute('INSERT INTO clients(code,name,contact,mobile,email,address,city,notes,created,modified) VALUES(?,?,?,?,?,?,?,?,?,?)',(code,name,vals['contact'].get().strip(),mobile,email,vals['address'].get().strip(),vals['city'].get().strip(),'Created during service entry',ts,ts)); cid=cur.lastrowid
                d.destroy(); refresh_lists(select_client_id=cid)
            tk.Button(d,text='Create & Select Client',command=save_client,bg=BLUE,fg='white',bd=0,padx=18,pady=9).pack(pady=18)

        def quick_equipment():
            cid=cmap.get(client.get())
            if not cid:return messagebox.showwarning('Select client','Select or create the client first.')
            d=tk.Toplevel(self); d.title('Quick Add Equipment'); d.geometry('540x520'); d.configure(bg=CARD); d.transient(self); d.grab_set()
            vals={}
            for key,label in [('make','Make *'),('model','Model *'),('serial','Serial Number'),('stock','Stock / External ID'),('type','Equipment Type'),('location','Location / Department')]:
                tk.Label(d,text=label,bg=CARD,fg=TEXT,font=('Segoe UI',9,'bold')).pack(anchor='w',padx=24,pady=(8,2)); vals[key]=ttk.Entry(d); vals[key].pack(fill='x',padx=24)
            no_serial=tk.BooleanVar(value=False)
            tk.Checkbutton(d,text='Serial number not available',variable=no_serial,bg=CARD,fg=TEXT,activebackground=CARD).pack(anchor='w',padx=20,pady=8)
            sold=tk.StringVar(value='Unknown'); row=tk.Frame(d,bg=CARD); row.pack(fill='x',padx=24); tk.Label(row,text='Sold By',bg=CARD,fg=TEXT,font=('Segoe UI',9,'bold')).pack(side='left'); ttk.Combobox(row,textvariable=sold,values=['Us','Other','Unknown'],state='readonly',width=15).pack(side='right')
            def save_equipment():
                make=vals['make'].get().strip(); model=vals['model'].get().strip(); serial=vals['serial'].get().strip()
                if not make or not model:return messagebox.showwarning('Required','Make and Model are mandatory.',parent=d)
                if not serial and not no_serial.get():return messagebox.showwarning('Serial','Enter the serial number or tick “Serial number not available”.',parent=d)
                with connect() as con:
                    if serial:
                        dup=con.execute('''SELECT e.id,e.code,e.make,e.model,e.serial,c.name client_name FROM equipment e LEFT JOIN clients c ON c.id=e.client_id
                                           WHERE LOWER(TRIM(e.serial))=LOWER(TRIM(?))''',(serial,)).fetchone()
                        if dup:
                            if messagebox.askyesno('Existing equipment found',f"{dup['code']} — {dup['make']} {dup['model']}\nS/N {dup['serial']}\nClient: {dup['client_name']}\n\nUse this existing SERVIX Equipment ID?",parent=d):
                                eid=dup['id']; d.destroy()
                                with connect() as c2: owner=c2.execute('SELECT client_id FROM equipment WHERE id=?',(eid,)).fetchone()[0]
                                refresh_lists(select_client_id=owner,select_equipment_id=eid); return
                            return messagebox.showwarning('Duplicate protected','The same physical serial should keep one SERVIX Equipment ID. Resolve ownership/history from Equipment before creating another record.',parent=d)
                    ts=now(); code=next_code('SEQ','equipment')
                    cur=con.execute('''INSERT INTO equipment(code,client_id,make,model,serial,stock_id,equipment_type,sold_by,location,notes,created,modified)
                                       VALUES(?,?,?,?,?,?,?,?,?,?,?,?)''',(code,cid,make,model,serial,vals['stock'].get().strip(),vals['type'].get().strip(),sold.get(),vals['location'].get().strip(),'Serial explicitly unavailable' if no_serial.get() else '',ts,ts)); eid=cur.lastrowid
                d.destroy(); refresh_lists(select_client_id=cid,select_equipment_id=eid)
            tk.Button(d,text='Create & Select Equipment',command=save_equipment,bg=BLUE,fg='white',bd=0,padx=18,pady=9).pack(pady=18)

        tk.Button(quick,text='+ Quick Add Client',command=quick_client,bg='#EAF2FF',fg=BLUE,bd=0,padx=12,pady=7).pack(side='left',padx=4)
        tk.Button(quick,text='+ Quick Add Equipment',command=quick_equipment,bg='#EAF7F8',fg='#087A84',bd=0,padx=12,pady=7).pack(side='left',padx=4)
        refresh_lists()

        tk.Label(form,text='Complaint / Requirement *',bg=CARD,fg=TEXT,font=('Segoe UI',8,'bold')).grid(row=10,column=0,sticky='w',padx=10,pady=(6,3))
        complaint=tk.Text(form,height=4,font=('Segoe UI',8),relief='solid',bd=1); complaint.grid(row=11,column=0,columnspan=3,sticky='ew',padx=10,pady=(0,8))

        guide=self.card(self.content); guide.pack(fill='x',padx=10,pady=(0,6))
        tk.Label(guide,text='* Mandatory   •   Engineer / Priority are important   •   Request Source is optional   •   Quote, charges, payment, work done and dispatch are completed later when relevant.',bg=CARD,fg=MUTED,font=('Segoe UI',8)).pack(anchor='w',padx=14,pady=10)

        actions=tk.Frame(self.content,bg=BG); actions.pack(fill='x',padx=10)
        def save():
            cid=cmap.get(client.get()); eid=emap.get(equip.get()); text=complaint.get('1.0','end').strip()
            if not cid or not eid or not reason.get() or not warranty.get() or not amc.get() or not text:return messagebox.showwarning('Mandatory information','Complete Client, Equipment, Reason, Complaint, Warranty and AMC.')
            with connect() as con:
                owner=con.execute('SELECT client_id FROM equipment WHERE id=?',(eid,)).fetchone()
                if not owner or owner[0]!=cid:return messagebox.showwarning('Equipment mismatch','Selected equipment does not belong to the selected client. Refresh the selection and try again.')
                if reason.get()=='Breakdown / Complaint':
                    serial=con.execute('SELECT serial FROM equipment WHERE id=?',(eid,)).fetchone()[0]
                    matches=repeat_complaints(eid,text)
                    if matches:
                        prev=matches[0]; days=get_setting('repeat_complaint_days','60')
                        if not messagebox.askyesno('Repeat complaint warning',f"This equipment has a similar complaint within {days} days: {prev['code']} ({prev['opened']}).\n\nPrevious complaint: {prev['complaint']}\n\nCreate a new Service ID anyway?",parent=self):return
                sc=next_code('SRV','services'); ts=now()
                cur=con.execute('''INSERT INTO services(code,client_id,equipment_id,opened,request_source,reason,complaint,warranty,amc,engineer,priority,status,payment_status,modified)
                                   VALUES(?,?,?,?,?,?,?,?,?,?,?,?,?,?)''',(sc,cid,eid,ts,source.get(),reason.get(),text,warranty.get(),amc.get(),engineer.get().strip(),priority.get() or 'Normal',status.get() or 'New','Not Applicable',ts))
                con.execute('INSERT INTO history(service_id,event_date,note,user) VALUES(?,?,?,?)',(cur.lastrowid,ts,'Service call created from office intake',self.current_user['username']))
            audit(self.current_user['username'],'service',sc,'CREATE','Service call created')
            if engineer.get().strip(): audit(self.current_user['username'],'service',sc,'ENGINEER_ASSIGN',f"Assigned to {engineer.get().strip()}")
            messagebox.showinfo('Service created',f'{sc} created successfully.'); self.show_service_detail(sc)
        tk.Button(actions,text='Create Service ID',command=save,bg=BLUE,fg='white',font=('Segoe UI',10,'bold'),bd=0,padx=22,pady=11).pack(side='right')

    def show_service_detail(self,code):
        self.clear()
        with connect() as con:r=con.execute('''SELECT s.*,c.name client,e.code equipment,e.make,e.model,e.serial FROM services s LEFT JOIN clients c ON c.id=s.client_id LEFT JOIN equipment e ON e.id=s.equipment_id WHERE s.code=?''',(code,)).fetchone()
        if not r:return
        bar=tk.Frame(self.content,bg='#164F7C',height=36); bar.pack(fill='x'); bar.pack_propagate(False)
        tk.Label(bar,text='Service Request - New / Edit',bg='#164F7C',fg='white',font=('Segoe UI',10,'bold')).pack(side='left',padx=14)
        tk.Label(bar,text='Service ID:',bg='#164F7C',fg='white',font=('Segoe UI',8)).pack(side='left',padx=(0,6))
        tk.Label(bar,text=code,bg='#FFF8B8',fg=TEXT,font=('Segoe UI',9,'bold'),padx=18,pady=3).pack(side='left')
        tk.Label(bar,text=f"{r['client']}  •  {r['equipment']}  •  {r['make']} {r['model']}",bg='#164F7C',fg='#DCECF8',font=('Segoe UI',8)).pack(side='right',padx=16)
        tabs=ttk.Notebook(self.content); tabs.pack(fill='both',expand=True,padx=10,pady=(6,10))
        ov=tk.Frame(tabs,bg=CARD); tech=tk.Frame(tabs,bg=CARD); parts_tab=tk.Frame(tabs,bg=CARD); cal_tab=tk.Frame(tabs,bg=CARD); att_tab=tk.Frame(tabs,bg=CARD); comm=tk.Frame(tabs,bg=CARD); location_tab=tk.Frame(tabs,bg=CARD); hist=tk.Frame(tabs,bg=CARD)
        tabs.add(ov,text=' 1. Client & Equipment ')
        tabs.add(cal_tab,text=' 4. Calibration Details ')
        tabs.add(comm,text=' 5. Commercial & Approval ')
        tabs.add(parts_tab,text=' 6. Parts Used ')
        tabs.add(tech,text=' 7. Work Done & Testing ')
        tabs.add(att_tab,text=' 8. Photos / Documents ')
        tabs.add(location_tab,text=' 9. Location / Movement ')
        tabs.add(hist,text=' 10. Communication History ')
        report_tab=tk.Frame(tabs,bg=CARD); close_tab=tk.Frame(tabs,bg=CARD)
        tabs.add(report_tab,text=' 11. Service Report ')
        tabs.add(close_tab,text=' 12. Completion & Closure ')
        tk.Label(report_tab,text='Service Report Preview',bg=CARD,fg=TEXT,font=('Segoe UI',14,'bold')).pack(anchor='w',padx=18,pady=(18,4))
        tk.Label(report_tab,text='Printable/PDF service report generation will use this service record, technical work, parts and calibration data.',bg=CARD,fg=MUTED,font=('Segoe UI',9)).pack(anchor='w',padx=18)
        summary=tk.Frame(report_tab,bg='#F7FAFD',highlightthickness=1,highlightbackground=BORDER); summary.pack(fill='x',padx=18,pady=16)
        for label,value in [('Service ID',code),('Client',r['client']),('Equipment',f"{r['make']} {r['model']} / {r['serial'] or 'No serial'}"),('Complaint',r['complaint']),('Work Done',r['work_done'] or 'Pending'),('Final Result',r['final_result'] or 'Pending')]:
            row=tk.Frame(summary,bg='#F7FAFD'); row.pack(fill='x',padx=12,pady=5); tk.Label(row,text=label,width=16,anchor='w',bg='#F7FAFD',fg=MUTED,font=('Segoe UI',8,'bold')).pack(side='left'); tk.Label(row,text=str(value),anchor='w',bg='#F7FAFD',fg=TEXT,font=('Segoe UI',8),wraplength=850,justify='left').pack(side='left',fill='x',expand=True)
        def export_service_pdf():
            filename=filedialog.asksaveasfilename(defaultextension='.pdf',initialfile=f"{code}-Service-Report.pdf",filetypes=[('PDF Report','*.pdf')])
            if not filename:return
            try:
                with connect() as con:
                    report_parts=con.execute('SELECT * FROM parts WHERE service_id=? ORDER BY id',(r['id'],)).fetchall()
                    report_cal=con.execute('SELECT * FROM calibration WHERE service_id=?',(r['id'],)).fetchone()
                create_service_report(filename,r,cli,eq,report_parts,report_cal,{'name':get_setting('company_name','HAC'),'title':get_setting('system_title','Service Management System')})
                with connect() as con: con.execute('INSERT INTO history(service_id,event_date,note,user) VALUES(?,?,?,?)',(r['id'],now(),'PDF Service Report generated','Office'))
                messagebox.showinfo('Service Report','PDF service report generated successfully.')
            except Exception as ex: messagebox.showerror('Service Report',f'Could not generate report:\n{ex}')
        tk.Button(report_tab,text='Generate PDF Service Report',command=export_service_pdf,bg=BLUE,fg='white',bd=0,padx=18,pady=9).pack(anchor='e',padx=18,pady=(0,16))
        tk.Label(close_tab,text='Completion & Closure',bg=CARD,fg=TEXT,font=('Segoe UI',14,'bold')).pack(anchor='w',padx=18,pady=(18,4))
        tk.Label(close_tab,text='Closure is controlled from Work Done & Testing. Required fields are checked before Closed status is accepted.',bg=CARD,fg=MUTED,font=('Segoe UI',9)).pack(anchor='w',padx=18)
        checks=tk.Frame(close_tab,bg='#F7FAFD',highlightthickness=1,highlightbackground=BORDER); checks.pack(fill='x',padx=18,pady=16)
        closure_checks=[('Engineer assigned',bool(r['engineer'])),('Work date recorded',bool(r['work_date'])),('Work performed recorded',bool(r['work_done'])),('Final result recorded',bool(r['final_result'] and r['final_result']!='Pending')),('Billing decision',bool(r['foc_chargeable'])),('Completion date',bool(r['completion_date']))]
        for label,ok in closure_checks: tk.Label(checks,text=('✓  ' if ok else '○  ')+label,bg='#F7FAFD',fg=GREEN if ok else ORANGE,font=('Segoe UI',9,'bold' if ok else 'normal')).pack(anchor='w',padx=14,pady=5)
        ov.grid_columnconfigure((0,1,2,3),weight=1); ov.grid_rowconfigure(0,weight=1)
        client_box=tk.LabelFrame(ov,text=' 1. Client Information ',bg=CARD,fg=BLUE,font=('Segoe UI',8,'bold'),highlightthickness=1,highlightbackground='#B8D8F3'); client_box.grid(row=0,column=0,sticky='nsew',padx=(5,2),pady=5)
        equip_box=tk.LabelFrame(ov,text=' 2. Equipment Information ',bg=CARD,fg=BLUE,font=('Segoe UI',8,'bold'),highlightthickness=1,highlightbackground='#B8D8F3'); equip_box.grid(row=0,column=1,sticky='nsew',padx=2,pady=5)
        service_box=tk.LabelFrame(ov,text=' 3. Service Details ',bg=CARD,fg=BLUE,font=('Segoe UI',8,'bold'),highlightthickness=1,highlightbackground='#B8D8F3'); service_box.grid(row=0,column=2,sticky='nsew',padx=2,pady=5)
        cal_summary=tk.LabelFrame(ov,text=' 4. Calibration Details ',bg=CARD,fg=BLUE,font=('Segoe UI',8,'bold'),highlightthickness=1,highlightbackground='#B8D8F3'); cal_summary.grid(row=0,column=3,sticky='nsew',padx=(2,5),pady=5)
        def readonly_row(parent,label,value,row):
            tk.Label(parent,text=label,bg=CARD,fg=MUTED,font=('Segoe UI',7)).grid(row=row,column=0,sticky='w',padx=(10,5),pady=4)
            e=ttk.Entry(parent,font=('Segoe UI',8)); e.grid(row=row,column=1,sticky='ew',padx=(0,10),pady=4); e.insert(0,str(value or '—')); e.configure(state='readonly'); parent.grid_columnconfigure(1,weight=1)
        with connect() as con:
            cli=con.execute('SELECT * FROM clients WHERE id=?',(r['client_id'],)).fetchone()
            eq=con.execute('SELECT * FROM equipment WHERE id=?',(r['equipment_id'],)).fetchone()
        for rr,(lab,val) in enumerate([('Client ID',cli['code']),('Client Name',cli['name']),('Contact Person',cli['contact']),('Mobile',cli['mobile']),('Email',cli['email']),('City',cli['city'])]): readonly_row(client_box,lab,val,rr)
        tk.Button(client_box,text='View Full Client Details',command=lambda:self.show_client_360(cli['code']),bg='#EAF4FF',fg=BLUE,bd=0,padx=10,pady=6).grid(row=7,column=0,columnspan=2,sticky='ew',padx=10,pady=8)
        for rr,(lab,val) in enumerate([('Equipment ID',eq['code']),('Make',eq['make']),('Model',eq['model']),('Serial No.',eq['serial'] or 'Not Available'),('Equipment Type',eq['equipment_type']),('Location',eq['location']),('Warranty Up To',eq['warranty_till']),('AMC Up To',eq['amc_till'])]): readonly_row(equip_box,lab,val,rr)
        tk.Button(equip_box,text='View Full Equipment History',command=lambda:self.show_equipment_360(eq['code']),bg='#EAF4FF',fg=BLUE,bd=0,padx=10,pady=6).grid(row=9,column=0,columnspan=2,sticky='ew',padx=10,pady=8)
        for rr,(lab,val) in enumerate([('Date of Complaint',r['opened']),('Reason for Service',r['reason']),('Priority',r['priority']),('Assigned Engineer',r['engineer'] or 'Unassigned'),('Current Status',r['status']),('Warranty',r['warranty']),('AMC',r['amc'])]): readonly_row(service_box,lab,val,rr)
        tk.Label(service_box,text='Complaint Details',bg=CARD,fg=MUTED,font=('Segoe UI',7)).grid(row=8,column=0,sticky='nw',padx=(10,5),pady=4)
        complaint=tk.Text(service_box,height=4,font=('Segoe UI',8),wrap='word'); complaint.grid(row=8,column=1,sticky='ew',padx=(0,10),pady=4); complaint.insert('1.0',r['complaint']); complaint.configure(state='disabled')
        with connect() as con: cal_head=con.execute('SELECT * FROM calibration WHERE service_id=?',(r['id'],)).fetchone()
        if r['reason']=='Calibration':
            cal_rows=[('Received Date',cal_head['received_date'] if cal_head else ''),('Performed Date',cal_head['calibration_date'] if cal_head else ''),('Result',cal_head['result'] if cal_head else 'Pending'),('Certificate No.',cal_head['certificate_no'] if cal_head else ''),('Certificate Date',cal_head['certificate_date'] if cal_head else ''),('Next Due',cal_head['next_due'] if cal_head else ''),('Performed By',cal_head['performed_by'] if cal_head else '')]
            for rr,(lab,val) in enumerate(cal_rows): readonly_row(cal_summary,lab,val,rr)
            tk.Button(cal_summary,text='Open Calibration Details',command=lambda:tabs.select(cal_tab),bg='#EAF4FF',fg=BLUE,bd=0,padx=8,pady=5).grid(row=8,column=0,columnspan=2,sticky='ew',padx=8,pady=8)
        else:
            tk.Label(cal_summary,text='Shown when Reason for Service is Calibration',bg=CARD,fg=MUTED,font=('Segoe UI',8),wraplength=180,justify='left').pack(anchor='nw',padx=12,pady=14)

        tech.grid_columnconfigure((0,1,2),weight=1)
        stage=tk.Frame(tech,bg='#F7FAFD',highlightthickness=1,highlightbackground=BORDER); stage.grid(row=1,column=0,columnspan=3,sticky='ew',padx=10,pady=(4,4))
        tk.Label(stage,text='WORKFLOW CONTROL',bg='#F7FAFD',fg=BLUE,font=('Segoe UI',8,'bold')).pack(side='left',padx=12,pady=8)
        tk.Label(stage,text=f"Current: {r['status']}   •   Complete only the fields required for the stage you are moving to.",bg='#F7FAFD',fg=MUTED,font=('Segoe UI',8)).pack(side='left',padx=8)
        stat=self.form_field(tech,'Status',2,0,['New','Acknowledged','Assigned','Equipment Awaited','Received','Visit Scheduled','Under Diagnosis','Awaiting Customer','Awaiting Approval','Awaiting Parts','Repair in Progress','Testing','Ready for Dispatch','Dispatched','Resolved','Closed','Reopened','Cancelled']); stat.set(r['status'])
        pending=self.form_field(tech,'Pending Reason',2,1,['','Awaiting Customer','Awaiting Parts','Awaiting Approval','Awaiting Payment','Awaiting Engineer','Other']); pending.set(r['pending_reason'] or '')
        eng=self.form_field(tech,'Engineer',2,2,[])
        with connect() as con: active_engineers=[x['name'] for x in con.execute('SELECT name FROM engineers WHERE active=1 ORDER BY name')]
        if r['engineer'] and r['engineer'] not in active_engineers: active_engineers.append(r['engineer'])
        eng['values']=active_engineers; eng.set(r['engineer'] or '')
        received=self.form_field(tech,'Equipment Received Date',4,0); received.insert(0,r['received_date'] or '')
        condition=self.form_field(tech,'Received Condition / Accessories',4,1); condition.insert(0,r['received_condition'] or '')
        work_date=self.form_field(tech,'Engineer Visit / Work Date',4,2); work_date.insert(0,r['work_date'] or '')
        diag=self.form_field(tech,'Diagnosis',6,0); diag.insert(0,r['diagnosis'] or '')
        root=self.form_field(tech,'Root Cause',6,1); root.insert(0,r['root_cause'] or '')
        work=self.form_field(tech,'Work Performed',6,2); work.insert(0,r['work_done'] or '')
        testing=self.form_field(tech,'Testing / Verification',8,0); testing.insert(0,r['testing_result'] or '')
        result=self.form_field(tech,'Final Result',8,1,['Pending','Successful','Partially Resolved','Not Resolved']); result.set(r['final_result'] or 'Pending')
        next_action=self.form_field(tech,'Next Action',8,2); next_action.insert(0,r['next_action'] or '')
        dispatch=self.form_field(tech,'Dispatch Date',10,0); dispatch.insert(0,r['dispatch_date'] or '')
        dispatch_mode=self.form_field(tech,'Dispatch Mode',10,1,['','Courier','Hand','Other']); dispatch_mode.set(r['dispatch_mode'] or '')
        dispatch_ref=self.form_field(tech,'Dispatch Reference / Remarks',10,2); dispatch_ref.insert(0,r['dispatch_reference'] or '')
        completion=self.form_field(tech,'Service Completion Date',12,0); completion.insert(0,r['completion_date'] or '')
        closure=self.form_field(tech,'Closure Date',12,1); closure.insert(0,r['closure_date'] or '')
        cancel_reason=self.form_field(tech,'Cancel / Reopen Reason',12,2); cancel_reason.insert(0,r['cancel_reason'] or '')

        update_box=tk.LabelFrame(tech,text=' Add chronological engineer / office update ',bg=CARD,fg=TEXT,font=('Segoe UI',9,'bold'))
        update_box.grid(row=14,column=0,columnspan=3,sticky='ew',padx=10,pady=10); update_box.grid_columnconfigure((0,1,2),weight=1)
        upd_type=self.form_field(update_box,'Update Type',0,0,['Engineer Update','Technical','Customer Communication','Follow-up','Management']); upd_type.set('Engineer Update')
        upd_date=self.form_field(update_box,'Date / Time',0,1); upd_date.insert(0,now())
        upd_eng=self.form_field(update_box,'Engineer',0,2,active_engineers); upd_eng.set(r['engineer'] or '')
        upd_diag=self.form_field(update_box,'Diagnosis / Update',2,0); upd_work=self.form_field(update_box,'Work Done',2,1); upd_next=self.form_field(update_box,'Next Action',2,2)
        def add_update():
            if not self.require_edit(): return
            if not upd_date.get().strip() or not (upd_diag.get().strip() or upd_work.get().strip()):return messagebox.showwarning('Update required','Enter the update date/time and Diagnosis/Update or Work Done.')
            with connect() as con:
                con.execute('''INSERT INTO service_updates(service_id,update_date,engineer,update_type,diagnosis,work_done,result,next_action,user) VALUES(?,?,?,?,?,?,?,?,?)''',(r['id'],upd_date.get().strip(),upd_eng.get().strip(),upd_type.get(),upd_diag.get().strip(),upd_work.get().strip(),result.get(),upd_next.get().strip(),'Office'))
                con.execute('INSERT INTO history(service_id,event_date,note,user) VALUES(?,?,?,?)',(r['id'],now(),f"{upd_type.get()}: {upd_work.get().strip() or upd_diag.get().strip()}",'Office'))
                con.execute('UPDATE services SET modified=? WHERE id=?',(now(),r['id']))
            self.show_service_detail(code)
        tk.Button(update_box,text='+ Add Update',command=add_update,bg='#EAF2FF',fg=BLUE,bd=0,padx=15,pady=8).grid(row=4,column=2,sticky='e',padx=10,pady=10)

        ucols=('Date','Type','Engineer','Diagnosis / Update','Work Done','Next Action'); utr=ttk.Treeview(tech,columns=ucols,show='headings',height=6)
        for x in ucols:utr.heading(x,text=x)
        utr.grid(row=16,column=0,columnspan=3,sticky='nsew',padx=10,pady=8)
        with connect() as con:
            for x in con.execute('SELECT update_date,update_type,engineer,diagnosis,work_done,next_action FROM service_updates WHERE service_id=? ORDER BY id DESC',(r['id'],)):utr.insert('','end',values=tuple(x))

        def save_tech():
            if not self.require_edit(): return
            target=stat.get(); missing=[]
            if target=='Received' and not received.get().strip():missing.append('Equipment Received Date')
            if target in ('Under Diagnosis','Repair in Progress','Testing','Ready for Dispatch','Dispatched','Resolved','Closed') and not eng.get().strip():missing.append('Engineer')
            if target in ('Ready for Dispatch','Dispatched','Resolved','Closed') and not work.get().strip():missing.append('Work Performed')
            if target in ('Ready for Dispatch','Dispatched','Resolved','Closed') and result.get() in ('','Pending'):missing.append('Final Result')
            if target in ('Ready for Dispatch','Dispatched','Resolved','Closed') and not work_date.get().strip():missing.append('Engineer Visit / Work Date')
            if target in ('Dispatched','Closed') and not dispatch.get().strip():missing.append('Dispatch Date')
            if target=='Dispatched' and not dispatch_mode.get():missing.append('Dispatch Mode')
            if target=='Closed' and not completion.get().strip():missing.append('Service Completion Date')
            if target=='Closed' and not closure.get().strip():missing.append('Closure Date')
            if target=='Closed' and not r['foc_chargeable']:missing.append('FOC / Chargeable (Commercial tab)')
            if target=='Closed' and r['foc_chargeable']=='Chargeable' and (not r['payment_status'] or r['payment_status']=='Not Applicable'):missing.append('Payment Status (Commercial tab)')
            if target in ('Cancelled','Reopened') and not cancel_reason.get().strip():missing.append('Cancel / Reopen Reason')
            if r['reason']=='Calibration' and target=='Closed':
                with connect() as con: cal=con.execute('SELECT calibration_date,result FROM calibration WHERE service_id=?',(r['id'],)).fetchone()
                if not cal or not cal['calibration_date'] or not cal['result']:missing.append('Calibration Date + Result')
            if missing:return messagebox.showwarning('Cannot complete this stage','Complete these required items first:\n\n• '+'\n• '.join(missing))
            if target.startswith('Awaiting') and not pending.get():return messagebox.showwarning('Pending reason','Select a Pending Reason for an Awaiting status.')
            old_status=r['status']
            with connect() as con:
                con.execute('''UPDATE services SET diagnosis=?,root_cause=?,work_done=?,testing_result=?,final_result=?,status=?,pending_reason=?,engineer=?,received_date=?,received_condition=?,work_date=?,dispatch_date=?,dispatch_mode=?,dispatch_reference=?,completion_date=?,closure_date=?,next_action=?,cancel_reason=?,modified=? WHERE code=?''',(diag.get().strip(),root.get().strip(),work.get().strip(),testing.get().strip(),result.get(),target,pending.get(),eng.get().strip(),received.get().strip(),condition.get().strip(),work_date.get().strip(),dispatch.get().strip(),dispatch_mode.get(),dispatch_ref.get().strip(),completion.get().strip(),closure.get().strip(),next_action.get().strip(),cancel_reason.get().strip(),now(),code))
                note=f"Status {old_status} → {target}" if old_status!=target else f"Technical record updated — {target}"
                if target in ('Cancelled','Reopened'): note+=f" — Reason: {cancel_reason.get().strip()}"
                con.execute('INSERT INTO history(service_id,event_date,note,user) VALUES(?,?,?,?)',(r['id'],now(),note,'Office'))
            messagebox.showinfo('Saved','Service workflow updated.'); self.show_service_detail(code)
        tk.Button(tech,text='Save Workflow Update',command=save_tech,bg=BLUE,fg='white',bd=0,padx=18,pady=9).grid(row=16,column=2,sticky='e',padx=10,pady=15)
        location_tab.grid_columnconfigure((0,1),weight=1)
        tk.Label(location_tab,text='Equipment Location & Movement',bg=CARD,fg=TEXT,font=('Segoe UI',14,'bold')).grid(row=0,column=0,columnspan=2,sticky='w',padx=18,pady=(18,3))
        tk.Label(location_tab,text='Optional operational locations only — use when equipment is collected, moved or returned.',bg=CARD,fg=MUTED,font=('Segoe UI',8)).grid(row=1,column=0,columnspan=2,sticky='w',padx=18,pady=(0,10))
        service_loc=self.form_field(location_tab,'Service / Site Location',2,0); service_loc.insert(0,r['service_location'] or (eq['location'] if eq else '') or '')
        pickup=self.form_field(location_tab,'Pickup / Collection Location',2,1); pickup.insert(0,r['pickup_location'] or '')
        drop=self.form_field(location_tab,'Drop / Return Location',4,0); drop.insert(0,r['drop_location'] or '')
        loc_notes=self.form_field(location_tab,'Location / Movement Notes',4,1); loc_notes.insert(0,r['location_notes'] or '')
        def save_location():
            with connect() as con:
                con.execute('UPDATE services SET service_location=?,pickup_location=?,drop_location=?,location_notes=?,modified=? WHERE id=?',(service_loc.get().strip(),pickup.get().strip(),drop.get().strip(),loc_notes.get().strip(),now(),r['id']))
                con.execute('INSERT INTO history(service_id,event_date,note,user) VALUES(?,?,?,?)',(r['id'],now(),'Location / movement details updated','Office'))
            messagebox.showinfo('Saved','Location and movement details saved.')
        tk.Button(location_tab,text='Save Location Details',command=save_location,bg=BLUE,fg='white',bd=0,padx=18,pady=8).grid(row=6,column=1,sticky='e',padx=10,pady=12)

        # Parts Used is integrated with Inventory. Stock issues are linked to this Service ID.
        pcols=('Part No.','Description','Qty','FOC / Chargeable','Amount','Remarks'); ptr=ttk.Treeview(parts_tab,columns=pcols,show='headings',height=10)
        for pc in pcols: ptr.heading(pc,text=pc)
        ptr.pack(fill='both',expand=True,padx=12,pady=(12,6))
        pform=tk.Frame(parts_tab,bg=CARD); pform.pack(fill='x',padx=12,pady=8)
        with connect() as con:
            inv=con.execute("""SELECT i.id,i.code,i.part_name,i.part_number,i.unit,
                COALESCE(SUM(CASE WHEN m.movement_type IN ('Opening','Receipt','Return','Adjustment +') THEN m.qty
                                  WHEN m.movement_type IN ('Issue','Adjustment -') THEN -m.qty ELSE 0 END),0) stock
                FROM inventory_items i LEFT JOIN inventory_movements m ON m.item_id=i.id
                WHERE i.active=1 GROUP BY i.id ORDER BY i.part_name""").fetchall()
        invmap={f"{x['code']} — {x['part_name']} ({x['stock']:g} {x['unit']})":x for x in inv}
        tk.Label(pform,text='Inventory Part',bg=CARD,fg=MUTED,font=('Segoe UI',8)).grid(row=0,column=0,sticky='w',padx=4)
        partsel=ttk.Combobox(pform,state='readonly',values=list(invmap),width=38); partsel.grid(row=1,column=0,padx=4,sticky='ew')
        pent={}
        for i,(key,label,width) in enumerate([('qty','Qty',8),('amount','Amount',10),('remarks','Remarks',22)],1):
            tk.Label(pform,text=label,bg=CARD,fg=MUTED,font=('Segoe UI',8)).grid(row=0,column=i,sticky='w',padx=4)
            pent[key]=ttk.Entry(pform,width=width); pent[key].grid(row=1,column=i,padx=4,sticky='ew')
        pcharge=ttk.Combobox(pform,width=15,state='readonly',values=['FOC','Chargeable']); pcharge.set('Chargeable'); pcharge.grid(row=1,column=4,padx=4)
        def refresh_parts():
            ptr.delete(*ptr.get_children())
            with connect() as con:
                for x in con.execute('SELECT id,part_no,description,qty,chargeable,amount,remarks FROM parts WHERE service_id=? ORDER BY id DESC',(r['id'],)): ptr.insert('','end',iid=str(x['id']),values=tuple(x)[1:])
        def save_part():
            if not self.require_edit(): return
            item=invmap.get(partsel.get())
            if not item:return messagebox.showwarning('Required','Select an active Inventory Part.')
            try: qty=float(pent['qty'].get() or 1); amount=float(pent['amount'].get() or 0)
            except ValueError:return messagebox.showwarning('Check values','Quantity and amount must be numeric.')
            if qty<=0:return messagebox.showwarning('Check quantity','Quantity must be greater than zero.')
            with connect() as con:
                stock=con.execute("""SELECT COALESCE(SUM(CASE WHEN movement_type IN ('Opening','Receipt','Return','Adjustment +') THEN qty
                    WHEN movement_type IN ('Issue','Adjustment -') THEN -qty ELSE 0 END),0) FROM inventory_movements WHERE item_id=?""",(item['id'],)).fetchone()[0]
                if qty>stock:return messagebox.showwarning('Insufficient stock',f"Available stock is {stock:g} {item['unit']}. Receive or adjust stock before issuing this quantity.")
                cur=con.execute('INSERT INTO parts(service_id,part_no,description,qty,chargeable,amount,remarks) VALUES(?,?,?,?,?,?,?)',(r['id'],item['part_number'] or item['code'],item['part_name'],qty,pcharge.get(),amount,pent['remarks'].get().strip()))
                con.execute('INSERT INTO inventory_movements(item_id,movement_date,movement_type,qty,service_id,reference,notes,username) VALUES(?,?,?,?,?,?,?,?)',(item['id'],now(),'Issue',qty,r['id'],r['code'],f"Service part row {cur.lastrowid}",self.current_user['username']))
            add_history(r['id'],f"Inventory issued: {item['part_name']} x {qty}",self.current_user['username'])
            audit(self.current_user['username'],'service',r['code'],'PART_ISSUE',f"{item['code']} {item['part_name']} x {qty}")
            partsel.set('')
            for x in pent.values():x.delete(0,'end')
            refresh_parts(); messagebox.showinfo('Part issued','Part recorded against the service and deducted from inventory.')
        tk.Button(pform,text='+ Issue Part',command=save_part,bg=BLUE,fg='white',bd=0,padx=14,pady=8).grid(row=1,column=5,padx=8)
        def return_part():
            if not self.require_edit(): return
            sel=ptr.selection()
            if not sel:return messagebox.showwarning('Select part','Select the issued part to return.')
            part_id=int(sel[0])
            with connect() as con:
                p=con.execute('SELECT * FROM parts WHERE id=? AND service_id=?',(part_id,r['id'])).fetchone()
                if not p:return messagebox.showwarning('Part','The selected service part no longer exists.')
                issue=con.execute("""SELECT m.*,i.code,i.part_name,i.unit FROM inventory_movements m JOIN inventory_items i ON i.id=m.item_id
                    WHERE m.service_id=? AND m.movement_type='Issue' AND m.notes=? ORDER BY m.id LIMIT 1""",(r['id'],f"Service part row {part_id}")).fetchone()
                if not issue:return messagebox.showwarning('Legacy part','This part was not issued from Inventory and cannot be stock-returned automatically.')
                already=con.execute("""SELECT COALESCE(SUM(qty),0) FROM inventory_movements
                    WHERE service_id=? AND item_id=? AND movement_type='Return' AND reference=?""",(r['id'],issue['item_id'],f"{r['code']}/PART-{part_id}")).fetchone()[0]
            remaining=float(p['qty'])-float(already or 0)
            if remaining<=0:return messagebox.showinfo('Already returned','The full issued quantity has already been returned to inventory.')
            qty=simpledialog.askfloat('Return Part',f"Return quantity for {issue['part_name']}\nMaximum: {remaining:g} {issue['unit']}",minvalue=0.000001,maxvalue=remaining,parent=self)
            if qty is None:return
            reason=simpledialog.askstring('Return reason','Reason for return / correction:',parent=self)
            if not reason or not reason.strip():return messagebox.showwarning('Reason required','A return reason is required for the audit trail.')
            if not messagebox.askyesno('Confirm Return',f"Return {qty:g} {issue['unit']} of {issue['part_name']} to inventory?\n\nThe original issue record will be preserved.",parent=self):return
            with connect() as con:
                con.execute('INSERT INTO inventory_movements(item_id,movement_date,movement_type,qty,service_id,reference,notes,username) VALUES(?,?,?,?,?,?,?,?)',(issue['item_id'],now(),'Return',qty,r['id'],f"{r['code']}/PART-{part_id}",reason.strip(),self.current_user['username']))
            add_history(r['id'],f"Inventory returned: {issue['part_name']} x {qty:g}. Reason: {reason.strip()}",self.current_user['username'])
            audit(self.current_user['username'],'service',r['code'],'PART_RETURN',f"{issue['code']} {issue['part_name']} x {qty:g}; {reason.strip()}")
            messagebox.showinfo('Returned','Stock returned successfully. The original issue remains in service history.')
        tk.Button(pform,text='Return Selected',command=return_part,bg='#6B7280',fg='white',bd=0,padx=12,pady=8).grid(row=1,column=6,padx=4)
        refresh_parts()

        # Calibration fields only matter when the service reason is Calibration.
        cal_tab.grid_columnconfigure((0,1),weight=1)
        cal_date=self.form_field(cal_tab,'Calibration Date',0,0); cal_result=self.form_field(cal_tab,'Result',0,1,['Pass','Fail'])
        cert=self.form_field(cal_tab,'Certificate No.',2,0); next_due=self.form_field(cal_tab,'Next Due Date',2,1); cal_remarks=self.form_field(cal_tab,'Remarks',4,0)
        with connect() as con: cr=con.execute('SELECT * FROM calibration WHERE service_id=?',(r['id'],)).fetchone()
        if cr:
            cal_date.insert(0,cr['calibration_date'] or ''); cal_result.set(cr['result'] or ''); cert.insert(0,cr['certificate_no'] or ''); next_due.insert(0,cr['next_due'] or ''); cal_remarks.insert(0,cr['remarks'] or '')
        def save_cal():
            if not self.require_edit(): return
            if r['reason']=='Calibration' and (not cal_date.get() or not cal_result.get()): return messagebox.showwarning('Required','Calibration Date and Result are required for calibration jobs.')
            upsert_calibration(r['id'],cal_date.get(),cal_result.get(),cert.get(),next_due.get(),cal_remarks.get()); add_history(r['id'],f"Calibration updated: {cal_result.get() or 'details saved'}"); messagebox.showinfo('Saved','Calibration information saved.')
        tk.Button(cal_tab,text='Save Calibration',command=save_cal,bg=BLUE,fg='white',bd=0,padx=18,pady=9).grid(row=6,column=1,sticky='e',padx=10,pady=15)
        if r['reason']!='Calibration': tk.Label(cal_tab,text='This service is not marked as Calibration. These fields are optional.',bg=CARD,fg=MUTED).grid(row=7,column=0,columnspan=2,pady=8)

        # Compact document cards aligned to the approved Service Request design.
        tk.Label(att_tab,text='Photos / Documents',bg=CARD,fg=TEXT,font=('Segoe UI',10,'bold')).pack(anchor='w',padx=10,pady=(10,3))
        cards=tk.Frame(att_tab,bg=CARD); cards.pack(fill='x',padx=8,pady=(2,5))
        details=tk.Frame(att_tab,bg=CARD); details.pack(fill='both',expand=True,padx=8,pady=(0,6))
        acols=('Document','Type','Original','Stored','Saved'); atr=ttk.Treeview(details,columns=acols,show='headings',height=7)
        for ac in acols: atr.heading(ac,text=ac)
        atr.pack(fill='both',expand=True)
        def human(n):
            n=float(n or 0)
            for unit in ('B','KB','MB','GB'):
                if n<1024:return f'{n:.0f} {unit}' if unit=='B' else f'{n:.1f} {unit}'
                n/=1024
            return f'{n:.1f} TB'
        def refresh_att():
            for w in cards.winfo_children(): w.destroy()
            for x in atr.get_children(): atr.delete(x)
            with connect() as con: docs=con.execute('SELECT original_name,kind,original_size,stored_size,created FROM attachments WHERE service_id=? ORDER BY id DESC',(r['id'],)).fetchall()
            for i,x in enumerate(docs[:4]):
                tile=tk.Frame(cards,bg='#F8FBFE',width=112,height=88,highlightthickness=1,highlightbackground='#C8DDF0'); tile.pack(side='left',padx=3); tile.pack_propagate(False)
                icon='PDF' if str(x['kind']).lower()=='pdf' or str(x['original_name']).lower().endswith('.pdf') else 'PHOTO'
                tk.Label(tile,text=icon,bg='#EAF4FF',fg=RED if icon=='PDF' else BLUE,font=('Segoe UI',8,'bold')).pack(fill='x',pady=(8,4))
                tk.Label(tile,text=x['original_name'],bg='#F8FBFE',fg=TEXT,font=('Segoe UI',7),wraplength=100,justify='center').pack(padx=4)
            
            for x in docs: atr.insert('','end',values=(x['original_name'],x['kind'],human(x['original_size']),human(x['stored_size']),x['created']))
        def attach():
            path=filedialog.askopenfilename(filetypes=[('Images / PDF','*.jpg *.jpeg *.png *.webp *.pdf'),('All files','*.*')])
            if not path:return
            try: meta=store_attachment(path,code)
            except Exception as ex:return messagebox.showerror('Attachment',str(ex))
            add_attachment(r['id'],meta); add_history(r['id'],f"Attachment added: {meta['original_name']}"); refresh_att()
        tk.Button(cards,text='+\nAdd Files',command=attach,bg='white',fg=BLUE,bd=1,relief='solid',font=('Segoe UI',8,'bold'),width=10,height=4).pack(side='left',padx=3)
        refresh_att()

        comm.grid_columnconfigure((0,1,2),weight=1)
        foc=self.form_field(comm,'Billing Decision',0,0,['','FOC','Chargeable']); foc.set(r['foc_chargeable'] or '')
        quote=self.form_field(comm,'Quotation / Approval Status',0,1,['','Quotation Sent','No Quotation - Verbal Discussion','Estimate Shared by Phone','Estimate Shared by Email/WhatsApp','Quotation Not Required','FOC','AMC Covered','Pending Decision']); quote.set(r['quote_status'] or '')
        pay=self.form_field(comm,'Payment Status',0,2,['Not Applicable','To Be Invoiced','Invoice Raised','Pending','Part Paid','Paid']); pay.set(r['payment_status'] or 'Not Applicable')
        svc=self.form_field(comm,'Service Charge',2,0); svc.insert(0,str(r['service_charge'] or ''))
        parts=self.form_field(comm,'Parts Charge',2,1); parts.insert(0,str(r['parts_charge'] or ''))
        qa=self.form_field(comm,'Quote Amount',2,2); qa.insert(0,str(r['quote_amount'] or ''))
        qno=self.form_field(comm,'Quote No.',4,0); qno.insert(0,r['quote_no'] or '')
        qdate=self.form_field(comm,'Quote Date',4,1); qdate.insert(0,r['quote_date'] or '')
        po=self.form_field(comm,'PO / Approval Reference',4,2); po.insert(0,r['po_reference'] or '')
        inv=self.form_field(comm,'Invoice No.',6,0); inv.insert(0,r['invoice_no'] or '')
        invdate=self.form_field(comm,'Invoice Date',6,1); invdate.insert(0,r['invoice_date'] or '')
        invamt=self.form_field(comm,'Invoice Amount',6,2); invamt.insert(0,str(r['invoice_amount'] or ''))

        def money(x):
            try:return float(x or 0)
            except:return 0
        paid_total=self.q1('SELECT COALESCE(SUM(amount),0) FROM payments WHERE service_id=?',(r['id'],))
        balance=max(0,money(r['invoice_amount'])-paid_total)
        summary=tk.Label(comm,text=f"Payments received: ₹{paid_total:,.2f}    Outstanding: ₹{balance:,.2f}",bg=CARD,fg=TEXT,font=('Segoe UI',10,'bold'))
        summary.grid(row=8,column=0,columnspan=3,sticky='w',padx=10,pady=8)

        def save_comm():
            if foc.get()=='FOC': pay.set('Not Applicable')
            if foc.get()=='Chargeable' and pay.get()=='Not Applicable': return messagebox.showwarning('Payment status','Select the applicable payment status for a chargeable service.')
            with connect() as con:
                con.execute('''UPDATE services SET foc_chargeable=?,quote_status=?,payment_status=?,service_charge=?,parts_charge=?,quote_amount=?,quote_no=?,quote_date=?,po_reference=?,invoice_no=?,invoice_date=?,invoice_amount=?,modified=? WHERE code=?''',(foc.get(),quote.get(),pay.get(),money(svc.get()),money(parts.get()),money(qa.get()),qno.get().strip(),qdate.get().strip(),po.get().strip(),inv.get().strip(),invdate.get().strip(),money(invamt.get()),now(),code))
                con.execute('INSERT INTO history(service_id,event_date,note,user) VALUES(?,?,?,?)',(r['id'],now(),f"Commercial update: {foc.get() or 'billing pending'} / {pay.get()}",'Office'))
            messagebox.showinfo('Saved','Commercial information saved.'); self.show_service_detail(code)
        tk.Button(comm,text='Save Commercial Update',command=save_comm,bg=BLUE,fg='white',bd=0,padx=18,pady=9).grid(row=10,column=2,sticky='e',padx=10,pady=10)

        discussion=tk.LabelFrame(comm,text=' Commercial discussion / approval log ',bg=CARD,fg=TEXT,font=('Segoe UI',9,'bold'))
        discussion.grid(row=12,column=0,columnspan=3,sticky='ew',padx=10,pady=8); discussion.grid_columnconfigure((0,1,2),weight=1)
        ddate=self.form_field(discussion,'Date / Time',0,0); ddate.insert(0,now())
        dperson=self.form_field(discussion,'Person / Customer',0,1)
        dmethod=self.form_field(discussion,'Method',0,2,['Phone','Email','WhatsApp','In Person','Other'])
        damount=self.form_field(discussion,'Amount Discussed',2,0)
        dapproved=self.form_field(discussion,'Approved?',2,1,['Pending','Yes','No']); dapproved.set('Pending')
        dnotes=self.form_field(discussion,'Discussion Notes',2,2)
        def add_discussion():
            if not dnotes.get().strip(): return messagebox.showwarning('Discussion','Enter discussion / approval notes.')
            with connect() as con:
                con.execute('INSERT INTO commercial_discussions(service_id,discussion_date,person,method,amount,approved,notes,user) VALUES(?,?,?,?,?,?,?,?)',(r['id'],ddate.get(),dperson.get().strip(),dmethod.get(),money(damount.get()),dapproved.get(),dnotes.get().strip(),'Office'))
                con.execute('INSERT INTO history(service_id,event_date,note,user) VALUES(?,?,?,?)',(r['id'],now(),f"Commercial discussion: {dnotes.get().strip()}",'Office'))
            self.show_service_detail(code)
        tk.Button(discussion,text='+ Add Discussion',command=add_discussion,bg='#EAF2FF',fg=BLUE,bd=0,padx=14,pady=8).grid(row=4,column=2,sticky='e',padx=10,pady=8)

        payment=tk.LabelFrame(comm,text=' Payment entry ',bg=CARD,fg=TEXT,font=('Segoe UI',9,'bold'))
        payment.grid(row=14,column=0,columnspan=3,sticky='ew',padx=10,pady=8); payment.grid_columnconfigure((0,1,2),weight=1)
        pdate=self.form_field(payment,'Payment Date',0,0); pdate.insert(0,today())
        pamount=self.form_field(payment,'Amount Received',0,1)
        pmode=self.form_field(payment,'Mode',0,2,['Bank Transfer','Cheque','Cash','UPI','Card','Other'])
        pref=self.form_field(payment,'Reference',2,0); pnote=self.form_field(payment,'Notes',2,1)
        def add_payment():
            amount=money(pamount.get())
            if amount<=0:return messagebox.showwarning('Payment','Enter an amount greater than zero.')
            with connect() as con:
                con.execute('INSERT INTO payments(service_id,payment_date,amount,mode,reference,notes,user) VALUES(?,?,?,?,?,?,?)',(r['id'],pdate.get(),amount,pmode.get(),pref.get().strip(),pnote.get().strip(),'Office'))
                total=con.execute('SELECT COALESCE(SUM(amount),0) FROM payments WHERE service_id=?',(r['id'],)).fetchone()[0]
                invoice=money(invamt.get()) or money(r['invoice_amount'])
                new_status='Paid' if invoice>0 and total>=invoice else 'Part Paid'
                con.execute('UPDATE services SET amount_received=?,payment_status=?,payment_reference=?,modified=? WHERE id=?',(total,new_status,pref.get().strip(),now(),r['id']))
                con.execute('INSERT INTO history(service_id,event_date,note,user) VALUES(?,?,?,?)',(r['id'],now(),f"Payment recorded: ₹{amount:,.2f} ({pmode.get() or 'mode not specified'})",'Office'))
            self.show_service_detail(code)
        tk.Button(payment,text='+ Record Payment',command=add_payment,bg=GREEN,fg='white',bd=0,padx=14,pady=8).grid(row=4,column=2,sticky='e',padx=10,pady=8)

        logs=tk.Frame(comm,bg=CARD); logs.grid(row=16,column=0,columnspan=3,sticky='nsew',padx=10,pady=8)
        lcols=('Date','Type','Person / Mode','Amount','Status / Reference','Notes'); ltr=ttk.Treeview(logs,columns=lcols,show='headings',height=7)
        for x in lcols:ltr.heading(x,text=x)
        ltr.pack(fill='both',expand=True)
        with connect() as con:
            for x in con.execute('SELECT discussion_date,person,method,amount,approved,notes FROM commercial_discussions WHERE service_id=? ORDER BY id DESC',(r['id'],)):
                ltr.insert('','end',values=(x['discussion_date'],'Discussion',x['person'] or x['method'],x['amount'],x['approved'],x['notes']))
            for x in con.execute('SELECT payment_date,mode,amount,reference,notes FROM payments WHERE service_id=? ORDER BY id DESC',(r['id'],)):
                ltr.insert('','end',values=(x['payment_date'],'Payment',x['mode'],x['amount'],x['reference'],' '+(x['notes'] or '')))

        cols=('Date','User','Update'); tr=ttk.Treeview(hist,columns=cols,show='headings'); [tr.heading(c,text=c) for c in cols]; tr.column('Date',width=150); tr.column('User',width=100); tr.column('Update',width=800); tr.pack(fill='both',expand=True,padx=12,pady=12)
        with connect() as con:
            sid=r['id']
            for x in con.execute('SELECT event_date,user,note FROM history WHERE service_id=? ORDER BY id DESC',(sid,)):tr.insert('','end',values=tuple(x))

    def show_clients(self):
        self.clear()
        head=tk.Frame(self.content,bg='#164F7C',height=38); head.pack(fill='x'); head.pack_propagate(False)
        tk.Label(head,text='Clients',bg='#164F7C',fg='white',font=('Segoe UI',10,'bold')).pack(side='left',padx=14)
        tk.Label(head,text='Client Master / Service Customers',bg='#164F7C',fg='#DCECF8',font=('Segoe UI',7)).pack(side='left',padx=8)
        body=tk.Frame(self.content,bg=BG); body.pack(fill='both',expand=True,padx=10,pady=8)
        tools=tk.Frame(body,bg=CARD,highlightthickness=1,highlightbackground=BORDER); tools.pack(fill='x',pady=(0,6))
        tk.Label(tools,text='Search Client',bg=CARD,fg=TEXT,font=('Segoe UI',8,'bold')).pack(side='left',padx=(10,5),pady=8)
        q=tk.StringVar(); ent=ttk.Entry(tools,textvariable=q,width=42); ent.pack(side='left',pady=7)
        tk.Label(tools,text='Name / Contact / Mobile / Email / City',bg=CARD,fg=MUTED,font=('Segoe UI',7)).pack(side='left',padx=8)
        tk.Button(tools,text='+ New Client',bg=BLUE,fg='white',bd=0,padx=13,pady=6,command=self.client_dialog).pack(side='right',padx=8,pady=5)
        card=self.card(body); card.pack(fill='both',expand=True)
        cols=('Client ID','Client Name','Contact Person','Mobile','Email','City'); tr=ttk.Treeview(card,columns=cols,show='headings')
        widths=(90,230,160,120,220,130)
        for col,w in zip(cols,widths): tr.heading(col,text=col); tr.column(col,width=w,minwidth=70,anchor='w')
        tr.pack(fill='both',expand=True,padx=7,pady=7)
        def load(*_):
            for i in tr.get_children(): tr.delete(i)
            term='%'+q.get().strip()+'%'
            with connect() as con:
                rows=con.execute('SELECT code,name,contact,mobile,email,city FROM clients WHERE ?="" OR name LIKE ? OR contact LIKE ? OR mobile LIKE ? OR email LIKE ? OR city LIKE ? ORDER BY id DESC',(q.get().strip(),term,term,term,term,term)).fetchall()
            for r in rows: tr.insert('','end',values=tuple(r))
        q.trace_add('write',load); load()
        tr.bind('<Double-1>',lambda e:self.show_client_360(tr.item(tr.focus(),'values')[0]) if tr.focus() else None)

    def show_client_360(self,code):
        self.clear()
        with connect() as con:
            r=con.execute('SELECT * FROM clients WHERE code=?',(code,)).fetchone()
            if not r:return
            eq=con.execute('SELECT * FROM equipment WHERE client_id=? ORDER BY id DESC',(r['id'],)).fetchall()
            svc=con.execute('''SELECT s.code,s.opened,e.code equipment,e.make,e.model,e.serial,s.reason,s.status,s.warranty,s.amc,s.foc_chargeable,s.payment_status
                               FROM services s LEFT JOIN equipment e ON e.id=s.equipment_id WHERE s.client_id=? ORDER BY s.id DESC''',(r['id'],)).fetchall()
        head=tk.Frame(self.content,bg='#164F7C',height=42); head.pack(fill='x'); head.pack_propagate(False)
        tk.Label(head,text=f"Client Details  •  {r['code']}",bg='#164F7C',fg='white',font=('Segoe UI',10,'bold')).pack(side='left',padx=14)
        tk.Label(head,text=r['name'],bg='#164F7C',fg='#DCECF8',font=('Segoe UI',9,'bold')).pack(side='left',padx=10)
        tk.Button(head,text='+ New Service',command=self.show_new_service,bg=GREEN,fg='white',bd=0,padx=12,pady=5).pack(side='right',padx=10,pady=6)
        metrics=tk.Frame(self.content,bg=BG); metrics.pack(fill='x',padx=10,pady=(8,0))
        self.metric(metrics,'Equipment',len(eq),BLUE); self.metric(metrics,'Total Services',len(svc),GREEN)
        self.metric(metrics,'Open Calls',sum(1 for x in svc if x['status'] not in ('Closed','Cancelled')),ORANGE)
        self.metric(metrics,'Payment Pending',sum(1 for x in svc if x['payment_status'] in ('Pending','Part Paid')),RED)
        info=self.card(self.content); info.pack(fill='x',padx=10,pady=7)
        details=[('Contact',r['contact']),('Mobile',r['mobile']),('Email',r['email']),('City',r['city']),('Address',r['address'])]
        for i,(k,v) in enumerate(details):
            tk.Label(info,text=k,bg=CARD,fg=MUTED,font=('Segoe UI',8)).grid(row=0,column=i,sticky='w',padx=12,pady=(10,2))
            tk.Label(info,text=v or '—',bg=CARD,fg=TEXT,font=('Segoe UI',9,'bold')).grid(row=1,column=i,sticky='w',padx=12,pady=(0,10))
            info.grid_columnconfigure(i,weight=1)
        tabs=ttk.Notebook(self.content); tabs.pack(fill='both',expand=True,padx=10,pady=(0,10))
        et=tk.Frame(tabs,bg=CARD); st=tk.Frame(tabs,bg=CARD); tabs.add(et,text=' Equipment '); tabs.add(st,text=' Service History ')
        ecols=('SERVIX ID','Make','Model','Serial','Stock / External ID','Warranty Till','AMC Till'); etr=ttk.Treeview(et,columns=ecols,show='headings')
        for x in ecols:etr.heading(x,text=x)
        etr.pack(fill='both',expand=True,padx=12,pady=12)
        for x in eq:etr.insert('','end',values=(x['code'],x['make'],x['model'],x['serial'],x['stock_id'],x['warranty_till'],x['amc_till']))
        etr.bind('<Double-1>',lambda e:self.show_equipment_360(etr.item(etr.focus(),'values')[0]) if etr.focus() else None)
        scols=('Service ID','Opened','Equipment','Make / Model','Serial','Reason','Status','Warranty','AMC','Billing','Payment'); strr=ttk.Treeview(st,columns=scols,show='headings')
        for x in scols:strr.heading(x,text=x)
        strr.pack(fill='both',expand=True,padx=12,pady=12)
        for x in svc:strr.insert('','end',values=(x['code'],x['opened'],x['equipment'],f"{x['make']} {x['model']}",x['serial'],x['reason'],x['status'],x['warranty'],x['amc'],x['foc_chargeable'] or '—',x['payment_status'] or '—'))
        strr.bind('<Double-1>',lambda e:self.show_service_detail(strr.item(strr.focus(),'values')[0]) if strr.focus() else None)

    def client_dialog(self):
        if not self.require_edit(): return
        d=tk.Toplevel(self); d.title('Add Client'); d.geometry('560x520'); d.configure(bg=CARD); vals={}; specs=[('name','Client / Company',True),('contact','Contact Person',False),('mobile','Mobile',False),('email','Email',False),('address','Address',False),('city','City',False),('notes','Notes',False)]
        for i,(k,l,req) in enumerate(specs):tk.Label(d,text=l+(' *' if req else ''),bg=CARD,fg=TEXT,font=('Segoe UI',9,'bold')).pack(anchor='w',padx=25,pady=(10,2)); vals[k]=ttk.Entry(d); vals[k].pack(fill='x',padx=25)
        def save():
            if not vals['name'].get() or (not vals['mobile'].get() and not vals['email'].get()):return messagebox.showwarning('Required','Client name and at least Mobile or Email are required.',parent=d)
            with connect() as con:
                dup=con.execute('SELECT code,name FROM clients WHERE (mobile<>"" AND mobile=?) OR (email<>"" AND LOWER(email)=LOWER(?))',(vals['mobile'].get().strip(),vals['email'].get().strip())).fetchone()
                if dup:
                    return messagebox.showwarning('Possible duplicate',f"Possible duplicate: {dup['code']} — {dup['name']}\n\nOpen/review the existing client before creating another. Duplicate override will be added under Administration with authorization and audit.",parent=d)
                ts=now(); con.execute('INSERT INTO clients(code,name,contact,mobile,email,address,city,notes,created,modified) VALUES(?,?,?,?,?,?,?,?,?,?)',(next_code('CLI','clients'),*[vals[k].get().strip() for k in ('name','contact','mobile','email','address','city','notes')],ts,ts))
            d.destroy(); self.show_clients()
        tk.Button(d,text='Save Client',command=save,bg=BLUE,fg='white',bd=0,padx=18,pady=9).pack(pady=20)

    def show_equipment(self):
        self.clear()
        head=tk.Frame(self.content,bg='#164F7C',height=38); head.pack(fill='x'); head.pack_propagate(False)
        tk.Label(head,text='Equipment',bg='#164F7C',fg='white',font=('Segoe UI',10,'bold')).pack(side='left',padx=14)
        tk.Label(head,text='Permanent Equipment Master / Service History',bg='#164F7C',fg='#DCECF8',font=('Segoe UI',7)).pack(side='left',padx=8)
        body=tk.Frame(self.content,bg=BG); body.pack(fill='both',expand=True,padx=10,pady=8)
        tools=tk.Frame(body,bg=CARD,highlightthickness=1,highlightbackground=BORDER); tools.pack(fill='x',pady=(0,6))
        tk.Label(tools,text='Search Equipment',bg=CARD,fg=TEXT,font=('Segoe UI',8,'bold')).pack(side='left',padx=(10,5),pady=8)
        q=tk.StringVar(); ttk.Entry(tools,textvariable=q,width=42).pack(side='left',pady=7)
        tk.Label(tools,text='Equipment ID / Client / Make / Model / Serial No.',bg=CARD,fg=MUTED,font=('Segoe UI',7)).pack(side='left',padx=8)
        tk.Button(tools,text='+ New Equipment',bg=BLUE,fg='white',bd=0,padx=13,pady=6,command=self.equipment_dialog).pack(side='right',padx=8,pady=5)
        card=self.card(body); card.pack(fill='both',expand=True)
        cols=('Equipment ID','Client','Make','Model','Serial No.','External ID','Warranty Up To','AMC Up To'); tr=ttk.Treeview(card,columns=cols,show='headings')
        widths=(100,220,120,120,140,110,105,105)
        for col,w in zip(cols,widths): tr.heading(col,text=col); tr.column(col,width=w,minwidth=70,anchor='w')
        tr.pack(fill='both',expand=True,padx=7,pady=7)
        def load(*_):
            for i in tr.get_children(): tr.delete(i)
            term='%'+q.get().strip()+'%'
            with connect() as con:
                rows=con.execute('''SELECT e.code,c.name,e.make,e.model,e.serial,e.stock_id,e.warranty_till,e.amc_till FROM equipment e LEFT JOIN clients c ON c.id=e.client_id WHERE ?="" OR e.code LIKE ? OR c.name LIKE ? OR e.make LIKE ? OR e.model LIKE ? OR e.serial LIKE ? ORDER BY e.id DESC''',(q.get().strip(),term,term,term,term,term)).fetchall()
            for r in rows: tr.insert('','end',values=tuple(r))
        q.trace_add('write',load); load()
        tr.bind('<Double-1>',lambda e:self.show_equipment_360(tr.item(tr.focus(),'values')[0]) if tr.focus() else None)

    def show_equipment_360(self,code):
        self.clear()
        with connect() as con:
            r=con.execute('''SELECT e.*,c.code client_code,c.name client_name FROM equipment e LEFT JOIN clients c ON c.id=e.client_id WHERE e.code=?''',(code,)).fetchone()
            if not r:return
            svc=con.execute('''SELECT code,opened,reason,complaint,warranty,amc,engineer,status,work_done,final_result,foc_chargeable,payment_status,dispatch_date
                               FROM services WHERE equipment_id=? ORDER BY id DESC''',(r['id'],)).fetchall()
            parts=con.execute('''SELECT p.part_no,p.description,p.qty,p.chargeable,p.amount,s.code service_code
                                 FROM parts p JOIN services s ON s.id=p.service_id WHERE s.equipment_id=? ORDER BY p.id DESC''',(r['id'],)).fetchall()
        head=tk.Frame(self.content,bg='#164F7C',height=42); head.pack(fill='x'); head.pack_propagate(False)
        tk.Label(head,text=f"Equipment Details  •  {r['code']}",bg='#164F7C',fg='white',font=('Segoe UI',10,'bold')).pack(side='left',padx=14)
        tk.Label(head,text=f"{r['make']} {r['model']}  •  S/N {r['serial'] or 'Not Available'}",bg='#164F7C',fg='#DCECF8',font=('Segoe UI',9,'bold')).pack(side='left',padx=10)
        tk.Button(head,text='+ New Service',command=self.show_new_service,bg=GREEN,fg='white',bd=0,padx=12,pady=5).pack(side='right',padx=10,pady=6)
        metrics=tk.Frame(self.content,bg=BG); metrics.pack(fill='x',padx=22)
        self.metric(metrics,'Lifetime Services',len(svc),BLUE); self.metric(metrics,'Warranty Calls',sum(1 for x in svc if x['warranty']=='Yes'),GREEN)
        self.metric(metrics,'AMC Calls',sum(1 for x in svc if x['amc']=='Yes'),CYAN); self.metric(metrics,'Parts Recorded',len(parts),ORANGE)
        info=self.card(self.content); info.pack(fill='x',padx=28,pady=14)
        vals=[('Client',f"{r['client_code']} — {r['client_name']}"),('Stock / External ID',r['stock_id']),('Type',r['equipment_type']),('Location',r['location']),('Warranty Till',r['warranty_till']),('AMC Till',r['amc_till'])]
        for i,(k,v) in enumerate(vals):
            tk.Label(info,text=k,bg=CARD,fg=MUTED,font=('Segoe UI',8)).grid(row=0,column=i,sticky='w',padx=10,pady=(10,2)); tk.Label(info,text=v or '—',bg=CARD,fg=TEXT,font=('Segoe UI',9,'bold')).grid(row=1,column=i,sticky='w',padx=10,pady=(0,10)); info.grid_columnconfigure(i,weight=1)
        tabs=ttk.Notebook(self.content); tabs.pack(fill='both',expand=True,padx=28,pady=(0,22))
        ht=tk.Frame(tabs,bg=CARD); pt=tk.Frame(tabs,bg=CARD); tabs.add(ht,text=' Lifetime Service History '); tabs.add(pt,text=' Parts History ')
        hcols=('Service ID','Opened','Reason','Complaint','Warranty','AMC','Engineer','Status','Work Done','Result','Billing','Payment','Dispatch'); htr=ttk.Treeview(ht,columns=hcols,show='headings')
        for x in hcols:htr.heading(x,text=x)
        htr.pack(fill='both',expand=True,padx=12,pady=12)
        for x in svc:htr.insert('','end',values=tuple(x))
        htr.bind('<Double-1>',lambda e:self.show_service_detail(htr.item(htr.focus(),'values')[0]) if htr.focus() else None)
        pcols=('Service ID','Part No.','Description','Qty','FOC / Chargeable','Amount'); ptr=ttk.Treeview(pt,columns=pcols,show='headings')
        for x in pcols:ptr.heading(x,text=x)
        ptr.pack(fill='both',expand=True,padx=12,pady=12)
        for x in parts:ptr.insert('','end',values=(x['service_code'],x['part_no'],x['description'],x['qty'],x['chargeable'],x['amount']))

    def equipment_dialog(self):
        if not self.require_edit(): return
        d=tk.Toplevel(self); d.title('Add Equipment'); d.geometry('650x650'); d.configure(bg=CARD)
        with connect() as con:clients=[(r['id'],f"{r['code']} — {r['name']}") for r in con.execute('SELECT id,code,name FROM clients ORDER BY name')]
        cmap={v:k for k,v in clients}; vals={}; specs=[('client','Client',list(cmap)),('make','Make',None),('model','Model',None),('serial','Serial Number',None),('stock','Stock / External Equipment ID',None),('type','Equipment Type',None),('sold','Sold By',['Us','Other','Unknown']),('warranty','Warranty Till',None),('amc','AMC Till',None),('location','Location / Department',None)]
        for k,l,v in specs:tk.Label(d,text=l+(' *' if k in ('client','make','model') else ''),bg=CARD,fg=TEXT,font=('Segoe UI',9,'bold')).pack(anchor='w',padx=25,pady=(7,2)); w=ttk.Combobox(d,values=v,state='readonly') if v is not None else ttk.Entry(d); w.pack(fill='x',padx=25); vals[k]=w
        def save():
            if not vals['client'].get() or not vals['make'].get() or not vals['model'].get():return messagebox.showwarning('Required','Client, Make and Model are mandatory.',parent=d)
            with connect() as con:
                if vals['serial'].get():
                    dup=con.execute('SELECT code FROM equipment WHERE LOWER(TRIM(serial))=LOWER(TRIM(?))',(vals['serial'].get(),)).fetchone()
                    if dup:return messagebox.showwarning('Existing equipment',f"Serial already exists as {dup['code']}. Reuse that permanent SERVIX Equipment ID instead of creating a duplicate.",parent=d)
                ts=now(); con.execute('''INSERT INTO equipment(code,client_id,make,model,serial,stock_id,equipment_type,sold_by,warranty_till,amc_till,location,created,modified) VALUES(?,?,?,?,?,?,?,?,?,?,?,?,?)''',(next_code('SEQ','equipment'),cmap[vals['client'].get()],vals['make'].get(),vals['model'].get(),vals['serial'].get(),vals['stock'].get(),vals['type'].get(),vals['sold'].get(),vals['warranty'].get(),vals['amc'].get(),vals['location'].get(),ts,ts))
            d.destroy(); self.show_equipment()
        tk.Button(d,text='Save Equipment',command=save,bg=BLUE,fg='white',bd=0,padx=18,pady=9).pack(pady=18)

    def simple_summary(self,title,subtitle,rows):
        self.clear(); self.heading(title,subtitle); holder=tk.Frame(self.content,bg=BG); holder.pack(fill='x',padx=22)
        for name,val,color in rows:self.metric(holder,name,val,color)
        box=self.card(self.content); box.pack(fill='both',expand=True,padx=28,pady=18); tk.Label(box,text='Use Service Calls and Equipment records for detailed entries. More dedicated controls will be added in the next build.',bg=CARD,fg=MUTED,font=('Segoe UI',10)).pack(pady=35)
    def show_warranty(self):
        self.clear()
        head=tk.Frame(self.content,bg='#164F7C',height=38); head.pack(fill='x'); head.pack_propagate(False)
        tk.Label(head,text='Warranty & AMC',bg='#164F7C',fg='white',font=('Segoe UI',10,'bold')).pack(side='left',padx=14)
        tk.Label(head,text='Equipment Coverage / Expiry Control',bg='#164F7C',fg='#DCECF8',font=('Segoe UI',7)).pack(side='left',padx=8)
        body=tk.Frame(self.content,bg=BG); body.pack(fill='both',expand=True,padx=10,pady=8)
        metrics=tk.Frame(body,bg=BG); metrics.pack(fill='x',pady=(0,6))
        self.metric(metrics,'Warranty Expiring',self.q1("SELECT COUNT(*) FROM equipment WHERE warranty_till!='' AND date(warranty_till)>=date('now') AND date(warranty_till)<=date('now','+30 day')"),ORANGE,'Next 30 days')
        self.metric(metrics,'AMC Expiring',self.q1("SELECT COUNT(*) FROM equipment WHERE amc_till!='' AND date(amc_till)>=date('now') AND date(amc_till)<=date('now','+60 day')"),BLUE,'Next 60 days')
        self.metric(metrics,'Warranty Expired',self.q1("SELECT COUNT(*) FROM equipment WHERE warranty_till!='' AND date(warranty_till)<date('now')"),RED,'Needs review')
        self.metric(metrics,'AMC Expired',self.q1("SELECT COUNT(*) FROM equipment WHERE amc_till!='' AND date(amc_till)<date('now')"),RED,'Needs review')
        tools=tk.Frame(body,bg=CARD,highlightthickness=1,highlightbackground=BORDER); tools.pack(fill='x',pady=(0,6))
        tk.Label(tools,text='Coverage Register',bg=CARD,fg=TEXT,font=('Segoe UI',8,'bold')).pack(side='left',padx=(10,8),pady=8)
        q=tk.StringVar(); ttk.Entry(tools,textvariable=q,width=30).pack(side='left',pady=6)
        mode=tk.StringVar(value='All Coverage'); cb=ttk.Combobox(tools,textvariable=mode,state='readonly',width=18,values=['All Coverage','Active','Expiring','Expired','Warranty','AMC']); cb.pack(side='left',padx=7,pady=6)
        tk.Label(tools,text='Double-click equipment to open full history',bg=CARD,fg=MUTED,font=('Segoe UI',7)).pack(side='right',padx=10)
        card=self.card(body); card.pack(fill='both',expand=True)
        cols=('Equipment ID','Client','Make / Model','Serial No.','Warranty Till','Warranty Status','AMC Till','AMC Status','Location'); tr=ttk.Treeview(card,columns=cols,show='headings')
        widths=(95,190,180,120,95,95,95,90,130)
        for x,w in zip(cols,widths):tr.heading(x,text=x); tr.column(x,width=w,minwidth=65,anchor='w')
        tr.tag_configure('expired',foreground='#B42318'); tr.tag_configure('expiring',foreground='#B54708'); tr.tag_configure('active',foreground='#16794A')
        tr.pack(fill='both',expand=True,padx=7,pady=7)
        def state(date_text,days):
            if not date_text:return 'Not Set'
            try:
                from datetime import datetime,date
                d=datetime.strptime(date_text,'%Y-%m-%d').date(); delta=(d-date.today()).days
                if delta<0:return 'Expired'
                if delta<=days:return 'Expiring'
                return 'Active'
            except:return 'Check Date'
        def load(*_):
            for x in tr.get_children():tr.delete(x)
            term=q.get().strip().lower(); filt=mode.get()
            with connect() as con: rows=con.execute("""SELECT e.code,c.name,e.make,e.model,e.serial,e.warranty_till,e.amc_till,e.location FROM equipment e LEFT JOIN clients c ON c.id=e.client_id WHERE COALESCE(e.warranty_till,'')!='' OR COALESCE(e.amc_till,'')!='' ORDER BY c.name,e.make,e.model""").fetchall()
            for r in rows:
                ws=state(r['warranty_till'],30); ams=state(r['amc_till'],60)
                hay=' '.join(str(r[k] or '') for k in r.keys()).lower()
                if term and term not in hay:continue
                if filt=='Active' and not (ws=='Active' or ams=='Active'):continue
                if filt=='Expiring' and not (ws=='Expiring' or ams=='Expiring'):continue
                if filt=='Expired' and not (ws=='Expired' or ams=='Expired'):continue
                if filt=='Warranty' and not r['warranty_till']:continue
                if filt=='AMC' and not r['amc_till']:continue
                tag='expired' if 'Expired' in (ws,ams) else ('expiring' if 'Expiring' in (ws,ams) else 'active')
                tr.insert('','end',values=(r['code'],r['name'],f"{r['make']} / {r['model']}",r['serial'] or 'Not Available',r['warranty_till'],ws,r['amc_till'],ams,r['location']),tags=(tag,))
        q.trace_add('write',load); cb.bind('<<ComboboxSelected>>',load); load()
        tr.bind('<Double-1>',lambda e:self.show_equipment_360(tr.item(tr.focus(),'values')[0]) if tr.focus() else None)

    def show_calibration(self):
        self.clear()
        top=tk.Frame(self.content,bg='#164F7C',height=38); top.pack(fill='x'); top.pack_propagate(False)
        tk.Label(top,text='Calibration Control',bg='#164F7C',fg='white',font=('Segoe UI',10,'bold')).pack(side='left',padx=14)
        tk.Label(top,text='Calibration Jobs / Certificates / Due-Date Control',bg='#164F7C',fg='#DCECF8',font=('Segoe UI',7)).pack(side='left',padx=8)
        metrics=tk.Frame(self.content,bg=BG); metrics.pack(fill='x',padx=10,pady=(8,0))
        self.metric(metrics,'Open Jobs',self.q1("SELECT COUNT(*) FROM services WHERE reason='Calibration' AND status NOT IN ('Closed','Cancelled')"),BLUE,'Active calibration work')
        self.metric(metrics,'Due in 30 Days',self.q1("SELECT COUNT(*) FROM calibration WHERE next_due!='' AND date(next_due)>=date('now') AND date(next_due)<=date('now','+30 day')"),ORANGE,'Plan customer follow-up')
        self.metric(metrics,'Overdue',self.q1("SELECT COUNT(*) FROM calibration WHERE next_due!='' AND date(next_due)<date('now')"),RED,'Requires attention')
        self.metric(metrics,'Passed',self.q1("SELECT COUNT(*) FROM calibration WHERE result='Pass'"),GREEN,'Recorded calibration results')
        card=self.card(self.content); card.pack(fill='both',expand=True,padx=10,pady=7)
        head=tk.Frame(card,bg=CARD); head.pack(fill='x',padx=14,pady=(12,4))
        tk.Label(head,text='Calibration Register',font=('Segoe UI',8,'bold'),bg=CARD,fg=TEXT).pack(side='left')
        q=tk.StringVar(); ttk.Entry(head,textvariable=q,width=28).pack(side='left',padx=10)
        tk.Label(head,text='Service / Client / Equipment / Serial / Certificate',bg=CARD,fg=MUTED,font=('Segoe UI',7)).pack(side='left')
        flt=ttk.Combobox(head,state='readonly',width=18,values=['All','Overdue','Due in 30 Days','Open Jobs']); flt.set('All'); flt.pack(side='right')
        cols=('Service ID','Client','Equipment','Make / Model','Serial','Calibration Date','Result','Certificate','Next Due','Status'); tr=ttk.Treeview(card,columns=cols,show='headings')
        widths=[115,180,115,180,120,110,80,120,110,120]
        for x,w in zip(cols,widths):tr.heading(x,text=x); tr.column(x,width=w,anchor='w')
        tr.pack(fill='both',expand=True,padx=14,pady=(6,14))
        def load(*_):
            for i in tr.get_children():tr.delete(i)
            where="s.reason='Calibration'"; choice=flt.get()
            if choice=='Overdue': where+=" AND cal.next_due!='' AND date(cal.next_due)<date('now')"
            elif choice=='Due in 30 Days': where+=" AND cal.next_due!='' AND date(cal.next_due)>=date('now') AND date(cal.next_due)<=date('now','+30 day')"
            elif choice=='Open Jobs': where+=" AND s.status NOT IN ('Closed','Cancelled')"
            sql=f'''SELECT s.code,c.name,e.code,e.make,e.model,e.serial,cal.calibration_date,cal.result,cal.certificate_no,cal.next_due,s.status
                    FROM services s LEFT JOIN clients c ON c.id=s.client_id LEFT JOIN equipment e ON e.id=s.equipment_id
                    LEFT JOIN calibration cal ON cal.service_id=s.id WHERE {where}
                    ORDER BY CASE WHEN cal.next_due IS NULL OR cal.next_due='' THEN 1 ELSE 0 END, cal.next_due, s.id DESC'''
            with connect() as con:
                for r in con.execute(sql):tr.insert('','end',values=(r['code'],r['name'],r['code'] if False else r[2],f"{r['make']} {r['model']}",r['serial'],r['calibration_date'],r['result'],r['certificate_no'],r['next_due'],r['status']))
        flt.bind('<<ComboboxSelected>>',load)
        def search_load(*_):
            load()
            term=q.get().strip().lower()
            if term:
                for item in list(tr.get_children()):
                    if term not in ' '.join(str(v or '') for v in tr.item(item,'values')).lower(): tr.delete(item)
        q.trace_add('write',search_load); load()
        tr.bind('<Double-1>',lambda e:self.show_service_detail(tr.item(tr.focus(),'values')[0]) if tr.focus() else None)

    def show_commercial(self):
        self.clear()
        head=tk.Frame(self.content,bg='#164F7C',height=38); head.pack(fill='x'); head.pack_propagate(False)
        tk.Label(head,text='Commercial & Payments',bg='#164F7C',fg='white',font=('Segoe UI',10,'bold')).pack(side='left',padx=14)
        tk.Label(head,text='Quotation / Approval / Invoice / Collection Control',bg='#164F7C',fg='#DCECF8',font=('Segoe UI',7)).pack(side='left',padx=8)
        body=tk.Frame(self.content,bg=BG); body.pack(fill='both',expand=True,padx=10,pady=8)
        metrics=tk.Frame(body,bg=BG); metrics.pack(fill='x',pady=(0,6))
        self.metric(metrics,'Quotation Pending',self.q1("SELECT COUNT(*) FROM services WHERE quote_status='Pending Decision'"),ORANGE,'Customer decision')
        self.metric(metrics,'To Be Invoiced',self.q1("SELECT COUNT(*) FROM services WHERE payment_status='To Be Invoiced'"),BLUE,'Chargeable jobs')
        self.metric(metrics,'Payment Pending',self.q1("SELECT COUNT(*) FROM services WHERE payment_status IN ('Pending','Payment Pending','Part Paid','Invoice Raised')"),RED,'Collection follow-up')
        outstanding=self.q1("SELECT COALESCE(SUM(MAX(0,COALESCE(invoice_amount,0)-COALESCE(amount_received,0))),0) FROM services WHERE foc_chargeable='Chargeable'")
        self.metric(metrics,'Outstanding ₹',f'{float(outstanding or 0):,.0f}',RED,'Chargeable services')
        tools=tk.Frame(body,bg=CARD,highlightthickness=1,highlightbackground=BORDER); tools.pack(fill='x',pady=(0,6))
        tk.Label(tools,text='Commercial Register',bg=CARD,fg=TEXT,font=('Segoe UI',8,'bold')).pack(side='left',padx=(10,8),pady=8)
        q=tk.StringVar(); ttk.Entry(tools,textvariable=q,width=28).pack(side='left',pady=6)
        mode=tk.StringVar(value='All'); cb=ttk.Combobox(tools,textvariable=mode,state='readonly',width=18,values=['All','Quotation Pending','Chargeable','FOC','To Be Invoiced','Payment Pending','Part Paid','Paid']); cb.pack(side='left',padx=7,pady=6)
        tk.Label(tools,text='Double-click a row to open the Service Request',bg=CARD,fg=MUTED,font=('Segoe UI',7)).pack(side='right',padx=10)
        card=self.card(body); card.pack(fill='both',expand=True)
        cols=('Service ID','Client','Equipment','Quotation / Approval','Billing','Invoice No.','Invoice Amount','Received','Outstanding','Payment Status','Service Status'); tr=ttk.Treeview(card,columns=cols,show='headings')
        widths=(100,175,105,180,85,100,100,90,95,115,115)
        for x,w in zip(cols,widths):tr.heading(x,text=x); tr.column(x,width=w,minwidth=65,anchor='w')
        tr.tag_configure('pending',foreground='#B42318'); tr.tag_configure('part',foreground='#B54708'); tr.tag_configure('paid',foreground='#16794A')
        tr.pack(fill='both',expand=True,padx=7,pady=7)
        def load(*_):
            for x in tr.get_children():tr.delete(x)
            term=q.get().strip().lower(); filt=mode.get()
            with connect() as con:
                rows=con.execute("""SELECT s.code,c.name,e.code equipment,s.quote_status,s.foc_chargeable,s.invoice_no,s.invoice_amount,s.amount_received,s.payment_status,s.status FROM services s LEFT JOIN clients c ON c.id=s.client_id LEFT JOIN equipment e ON e.id=s.equipment_id ORDER BY s.id DESC""").fetchall()
            for r in rows:
                inv=float(r['invoice_amount'] or 0); rec=float(r['amount_received'] or 0); bal=max(0,inv-rec)
                hay=' '.join(str(r[k] or '') for k in r.keys()).lower()
                if term and term not in hay:continue
                if filt=='Quotation Pending' and r['quote_status']!='Pending Decision':continue
                if filt in ('Chargeable','FOC') and r['foc_chargeable']!=filt:continue
                if filt=='To Be Invoiced' and r['payment_status']!='To Be Invoiced':continue
                if filt=='Payment Pending' and r['payment_status'] not in ('Pending','Payment Pending','Invoice Raised'):continue
                if filt=='Part Paid' and r['payment_status']!='Part Paid':continue
                if filt=='Paid' and r['payment_status']!='Paid':continue
                tag='paid' if r['payment_status']=='Paid' else ('part' if r['payment_status']=='Part Paid' else ('pending' if bal>0 or r['quote_status']=='Pending Decision' else ''))
                tr.insert('','end',values=(r['code'],r['name'],r['equipment'],r['quote_status'] or '—',r['foc_chargeable'] or '—',r['invoice_no'] or '—',f'₹{inv:,.2f}',f'₹{rec:,.2f}',f'₹{bal:,.2f}',r['payment_status'] or '—',r['status']),tags=(tag,) if tag else ())
        q.trace_add('write',load); cb.bind('<<ComboboxSelected>>',load); load()
        tr.bind('<Double-1>',lambda e:self.show_service_detail(tr.item(tr.focus(),'values')[0]) if tr.focus() else None)

    def show_reports(self):
        self.clear()
        topbar=tk.Frame(self.content,bg='#164F7C',height=38); topbar.pack(fill='x'); topbar.pack_propagate(False)
        tk.Label(topbar,text='Reports & Analytics',bg='#164F7C',fg='white',font=('Segoe UI',10,'bold')).pack(side='left',padx=14)
        tk.Label(topbar,text='Operational Filters / Management View / Export',bg='#164F7C',fg='#DCECF8',font=('Segoe UI',7)).pack(side='left',padx=8)
        filters=self.card(self.content); filters.pack(fill='x',padx=10,pady=(8,6))
        bar=tk.Frame(filters,bg=CARD); bar.pack(fill='x',padx=14,pady=12)
        tk.Label(bar,text='From',bg=CARD,fg=MUTED).pack(side='left'); from_e=ttk.Entry(bar,width=12); from_e.pack(side='left',padx=(5,12))
        tk.Label(bar,text='To',bg=CARD,fg=MUTED).pack(side='left'); to_e=ttk.Entry(bar,width=12); to_e.pack(side='left',padx=(5,12))
        tk.Label(bar,text='Status',bg=CARD,fg=MUTED).pack(side='left'); status=ttk.Combobox(bar,state='readonly',width=17,values=['All','Open','Closed','Awaiting Parts','Awaiting Customer','Dispatched']); status.set('All'); status.pack(side='left',padx=(5,12))
        tk.Label(bar,text='Coverage',bg=CARD,fg=MUTED).pack(side='left'); coverage=ttk.Combobox(bar,state='readonly',width=15,values=['All','Warranty','AMC','OOW','FOC','Chargeable']); coverage.set('All'); coverage.pack(side='left',padx=(5,12))
        tk.Label(bar,text='Reason',bg=CARD,fg=MUTED).pack(side='left'); reason=ttk.Combobox(bar,state='readonly',width=18,values=['All','Breakdown / Complaint','Calibration','Preventive Maintenance','AMC Preventive Visit','Installation / Commissioning','Inspection / Check-up']); reason.set('All'); reason.pack(side='left',padx=(5,8))

        metrics=tk.Frame(self.content,bg=BG); metrics.pack(fill='x',padx=10,pady=(0,6))
        cards=[]
        for title,accent in [('Records',BLUE),('Open',ORANGE),('Closed',GREEN),('Outstanding ₹',RED)]: cards.append(self.metric(metrics,title,'-',accent,'Current filter'))

        table=self.card(self.content); table.pack(fill='both',expand=True,padx=10,pady=(0,6))
        top=tk.Frame(table,bg=CARD); top.pack(fill='x',padx=14,pady=(12,4)); tk.Label(top,text='Service Report',bg=CARD,fg=TEXT,font=('Segoe UI',8,'bold')).pack(side='left')
        cols=('Service ID','Opened','Client','Equipment','Reason','Engineer','Status','Coverage','Billing','Payment','Outstanding'); tr=ttk.Treeview(table,columns=cols,show='headings',height=13)
        for x,w in zip(cols,[115,105,180,120,155,115,130,95,95,105,105]): tr.heading(x,text=x); tr.column(x,width=w,anchor='w')
        tr.pack(fill='both',expand=True,padx=14,pady=(4,8))
        current=[]
        def query_rows():
            wh=[]; args=[]
            if from_e.get().strip(): wh.append('date(s.opened)>=date(?)'); args.append(from_e.get().strip())
            if to_e.get().strip(): wh.append('date(s.opened)<=date(?)'); args.append(to_e.get().strip())
            st=status.get()
            if st=='Open': wh.append("s.status NOT IN ('Closed','Cancelled')")
            elif st!='All': wh.append('s.status=?'); args.append(st)
            cov=coverage.get()
            if cov=='Warranty': wh.append("s.warranty='Yes'")
            elif cov=='AMC': wh.append("s.amc='Yes'")
            elif cov=='OOW': wh.append("s.warranty='No' AND s.amc='No'")
            elif cov in ('FOC','Chargeable'): wh.append('s.foc_chargeable=?'); args.append(cov)
            if reason.get()!='All': wh.append('s.reason=?'); args.append(reason.get())
            where=(' WHERE '+' AND '.join(wh)) if wh else ''
            sql='''SELECT s.code,s.opened,c.name,e.code,s.reason,COALESCE(s.engineer,''),s.status,
                    CASE WHEN s.warranty='Yes' THEN 'Warranty' WHEN s.amc='Yes' THEN 'AMC' ELSE 'OOW' END coverage,
                    COALESCE(s.foc_chargeable,''),COALESCE(s.payment_status,''),MAX(0,COALESCE(s.invoice_amount,0)-COALESCE(s.amount_received,0)) outstanding
                    FROM services s LEFT JOIN clients c ON c.id=s.client_id LEFT JOIN equipment e ON e.id=s.equipment_id'''+where+' ORDER BY s.id DESC'
            with connect() as con:return con.execute(sql,args).fetchall()
        def apply():
            nonlocal current; current=query_rows()
            for i in tr.get_children():tr.delete(i)
            for r in current:tr.insert('','end',values=tuple(r))
            vals=[len(current),sum(1 for r in current if r['status'] not in ('Closed','Cancelled')),sum(1 for r in current if r['status']=='Closed'),sum(float(r['outstanding'] or 0) for r in current)]
            for card,val in zip(cards,vals):
                labels=[w for w in card.winfo_children() if isinstance(w,tk.Label)]
                if len(labels)>1: labels[1].config(text=f'{val:,.2f}' if isinstance(val,float) else str(val))
        tk.Button(bar,text='Apply Filters',command=apply,bg=BLUE,fg='white',bd=0,padx=15,pady=7).pack(side='right')
        def export():
            if not current: apply()
            path=filedialog.asksaveasfilename(defaultextension='.csv',filetypes=[('CSV','*.csv')],initialfile='SERVIX_Filtered_Service_Report.csv')
            if not path:return
            with open(path,'w',newline='',encoding='utf-8-sig') as fh:
                w=csv.writer(fh); w.writerow(cols); w.writerows([tuple(r) for r in current])
            with connect() as con:con.execute('INSERT INTO exports(export_date,from_date,to_date,filename,record_count) VALUES(?,?,?,?,?)',(now(),from_e.get().strip(),to_e.get().strip(),path,len(current)))
            messagebox.showinfo('Export complete',f'{len(current)} filtered service records exported.')
        tk.Button(top,text='Export Current View to CSV',command=export,bg=GREEN,fg='white',bd=0,padx=14,pady=7).pack(side='right')
        tr.bind('<Double-1>',lambda e:self.show_service_detail(tr.item(tr.focus(),'values')[0]) if tr.focus() else None)
        apply()

        hist=self.card(self.content); hist.pack(fill='x',padx=28,pady=(0,18))
        tk.Label(hist,text='Recent Export History',bg=CARD,fg=TEXT,font=('Segoe UI',11,'bold')).pack(anchor='w',padx=14,pady=(10,4))
        with connect() as con: rows=con.execute('SELECT export_date,from_date,to_date,filename,record_count FROM exports ORDER BY id DESC LIMIT 5').fetchall()
        for x in rows: tk.Label(hist,text=f"{x['export_date']}  •  {x['record_count']} records  •  {Path(x['filename']).name}",bg=CARD,fg=MUTED,font=('Segoe UI',8)).pack(anchor='w',padx=14,pady=2)
        if not rows: tk.Label(hist,text='No exports recorded yet.',bg=CARD,fg=MUTED,font=('Segoe UI',8)).pack(anchor='w',padx=14,pady=(2,10))

    def show_data_management(self):
        if not self.require('data'): return
        self.clear()
        h=tk.Frame(self.content,bg='#164F7C',height=38); h.pack(fill='x'); h.pack_propagate(False)
        tk.Label(h,text='Data Export / Import',bg='#164F7C',fg='white',font=('Segoe UI',10,'bold')).pack(side='left',padx=14)
        tk.Label(h,text='Backup / Restore / Portable CSV Export',bg='#164F7C',fg='#DCECF8',font=('Segoe UI',7)).pack(side='left',padx=8)
        body=tk.Frame(self.content,bg=BG); body.pack(fill='both',expand=True,padx=10,pady=8)
        def panel(title,desc):
            p=self.card(body); p.pack(fill='x',pady=(0,7))
            tk.Label(p,text=title,bg=CARD,fg=TEXT,font=('Segoe UI',9,'bold')).pack(anchor='w',padx=14,pady=(10,2))
            tk.Label(p,text=desc,bg=CARD,fg=MUTED,font=('Segoe UI',8)).pack(anchor='w',padx=14,pady=(0,8)); return p
        b=panel('Complete Backup','Creates one ZIP containing the live SQLite database, attachments and a manifest. Use before upgrades or major data changes.')
        def backup():
            dest=filedialog.asksaveasfilename(title='Save SERVIX Backup',defaultextension='.zip',filetypes=[('SERVIX Backup','*.zip')],initialfile='SERVIX_Backup_'+datetime.datetime.now().strftime('%Y%m%d_%H%M')+'.zip')
            if not dest:return
            try:
                with connect() as con: con.execute('PRAGMA wal_checkpoint(FULL)')
                with zipfile.ZipFile(dest,'w',zipfile.ZIP_DEFLATED) as z:
                    z.write(DB,'data/servix.db')
                    att=DATA_ROOT/'attachments'
                    if att.exists():
                        for p in att.rglob('*'):
                            if p.is_file(): z.write(p,'attachments/'+str(p.relative_to(att)))
                    manifest={'product':'SERVIX','created':datetime.datetime.now().isoformat(timespec='seconds'),'database':'data/servix.db','attachments':True}
                    z.writestr('manifest.json',json.dumps(manifest,indent=2))
                with connect() as con: con.execute('INSERT INTO backup_history(backup_date,filename,status,notes) VALUES(?,?,?,?)',(now(),dest,'Success','Complete manual backup'))
                audit(self.current_user['username'],'backup',Path(dest).name,'CREATE','Complete backup created')
                messagebox.showinfo('Backup complete','SERVIX backup created successfully.\n\n'+dest)
            except Exception as ex: messagebox.showerror('Backup failed',str(ex))
        tk.Button(b,text='Create Complete Backup',command=backup,bg=BLUE,fg='white',bd=0,padx=14,pady=7).pack(anchor='w',padx=14,pady=(0,12))
        r=panel('Restore Backup','Restores a SERVIX backup ZIP. A safety copy of the current database is created first. SERVIX should be restarted after restore.')
        def restore():
            src=filedialog.askopenfilename(title='Select SERVIX Backup',filetypes=[('SERVIX Backup','*.zip')])
            if not src:return
            if not messagebox.askyesno('Confirm restore','Restore this backup? Current data will be replaced after a safety copy is created.'):return
            try:
                with zipfile.ZipFile(src) as z:
                    if 'manifest.json' not in z.namelist() or 'data/servix.db' not in z.namelist(): raise ValueError('This is not a valid SERVIX backup.')
                    safety=DB.with_name('servix_before_restore_'+datetime.datetime.now().strftime('%Y%m%d_%H%M%S')+'.db'); shutil.copy2(DB,safety)
                    tmp=DB.with_suffix('.restore'); tmp.write_bytes(z.read('data/servix.db')); shutil.move(str(tmp),str(DB))
                    att=DATA_ROOT/'attachments'; att.mkdir(parents=True,exist_ok=True)
                    for n in z.namelist():
                        if n.startswith('attachments/') and not n.endswith('/'):
                            rel=Path(n).relative_to('attachments'); target=att/rel; target.parent.mkdir(parents=True,exist_ok=True); target.write_bytes(z.read(n))
                audit(self.current_user['username'],'backup',Path(src).name,'RESTORE','Validated SERVIX backup restored')
                messagebox.showinfo('Restore complete','Backup restored. Please close and reopen SERVIX before continuing.')
            except Exception as ex: messagebox.showerror('Restore failed',str(ex))
        tk.Button(r,text='Restore Backup',command=restore,bg='#EAF2FF',fg=BLUE,bd=0,padx=14,pady=7).pack(anchor='w',padx=14,pady=(0,12))
        x=panel('Portable Data Export','Exports every SQLite table to separate CSV files inside one ZIP, plus a manifest. This does not modify SERVIX data.')
        def export_all():
            dest=filedialog.asksaveasfilename(title='Export SERVIX Data',defaultextension='.zip',filetypes=[('ZIP Archive','*.zip')],initialfile='SERVIX_Data_Export_'+datetime.datetime.now().strftime('%Y%m%d_%H%M')+'.zip')
            if not dest:return
            try:
                import io
                with connect() as con:
                    tables=[r[0] for r in con.execute("SELECT name FROM sqlite_master WHERE type='table' AND name NOT LIKE 'sqlite_%' ORDER BY name")]
                    with zipfile.ZipFile(dest,'w',zipfile.ZIP_DEFLATED) as z:
                        for table in tables:
                            rows=con.execute('SELECT * FROM "'+table.replace('"','""')+'"').fetchall(); out=io.StringIO(newline=''); w=csv.writer(out)
                            if rows:w.writerow(rows[0].keys()); w.writerows([tuple(r) for r in rows])
                            else:
                                cols=[r[1] for r in con.execute('PRAGMA table_info("'+table.replace('"','""')+'")')]; w.writerow(cols)
                            z.writestr('tables/'+table+'.csv',out.getvalue())
                        z.writestr('manifest.json',json.dumps({'product':'SERVIX','created':datetime.datetime.now().isoformat(timespec='seconds'),'tables':tables},indent=2))
                audit(self.current_user['username'],'export',Path(dest).name,'CREATE','All database tables exported to CSV ZIP')
                messagebox.showinfo('Export complete','Portable data export created successfully.\n\n'+dest)
            except Exception as ex: messagebox.showerror('Export failed',str(ex))
        tk.Button(x,text='Export All Tables (CSV ZIP)',command=export_all,bg=GREEN,fg='white',bd=0,padx=14,pady=(0,12))
        imp=panel('Controlled Client Import','Imports Clients from CSV with validation and duplicate protection. Required: Name and either Mobile or Email. Existing mobile/email records are skipped.')
        def import_clients():
            src=filedialog.askopenfilename(title='Select Client CSV',filetypes=[('CSV Files','*.csv')])
            if not src:return
            try:
                with open(src,'r',encoding='utf-8-sig',newline='') as fh:
                    reader=csv.DictReader(fh); headers={str(x).strip().lower():x for x in (reader.fieldnames or [])}
                    def col(row,*names):
                        for n in names:
                            if n in headers:return (row.get(headers[n]) or '').strip()
                        return ''
                    rows=list(reader)
                if not rows:return messagebox.showwarning('Import','CSV contains no data rows.')
                valid=[]; errors=[]; seen_mobile=set(); seen_email=set()
                with connect() as con:
                    for n,row in enumerate(rows,2):
                        name=col(row,'name','client name','customer name'); mobile=col(row,'mobile','phone','mobile no'); email=col(row,'email','email id').lower()
                        mobile_key=''.join(ch for ch in mobile if ch.isdigit())
                        contact=col(row,'contact','contact person'); address=col(row,'address'); city=col(row,'city')
                        if not name or (not mobile and not email):errors.append(f'Row {n}: Name and Mobile or Email required');continue
                        if mobile_key and mobile_key in seen_mobile:errors.append(f'Row {n}: duplicate mobile inside CSV');continue
                        if email and email in seen_email:errors.append(f'Row {n}: duplicate email inside CSV');continue
                        if mobile_key:seen_mobile.add(mobile_key)
                        if email:seen_email.add(email)
                        dup=con.execute("SELECT code,name FROM clients WHERE (?<>'' AND REPLACE(REPLACE(REPLACE(REPLACE(mobile,' ',''),'-',''),'(',''),')','')=?) OR (?<>'' AND lower(trim(email))=?)",(mobile_key,mobile_key,email,email)).fetchone()
                        if dup:errors.append(f"Row {n}: matches existing {dup['code']} {dup['name']}");continue
                        valid.append((name,contact,mobile,email,address,city))
                summary=f'Rows: {len(rows)}\\nReady to import: {len(valid)}\\nSkipped / invalid: {len(errors)}'
                if errors:summary+='\\n\\nFirst issues:\\n'+'\\n'.join(errors[:8])
                if not valid:return messagebox.showwarning('Import validation',summary)
                if not messagebox.askyesno('Confirm Client Import',summary+'\\n\\nImport the validated records?'):return
                with connect() as con:
                    for name,contact,mobile,email,address,city in valid:
                        code=next_code('CLI','clients')
                        con.execute('INSERT INTO clients(code,name,contact,mobile,email,address,city,created,modified) VALUES(?,?,?,?,?,?,?,?,?)',(code,name,contact,mobile,email,address,city,now(),now()))
                audit(self.current_user['username'],'clients','CSV','IMPORT',f'{len(valid)} imported; {len(errors)} skipped from {Path(src).name}')
                messagebox.showinfo('Import complete',f'{len(valid)} clients imported.\\n{len(errors)} rows skipped.')
            except Exception as ex:messagebox.showerror('Client import failed',str(ex))
        tk.Button(imp,text='Validate & Import Clients CSV',command=import_clients,bg=BLUE,fg='white',bd=0,padx=14,pady=7).pack(anchor='w',padx=14,pady=(0,12))
        eqimp=panel('Controlled Equipment Import','Imports equipment against an existing SERVIX Client. Required: Client ID, Make, Model and Serial. Use NOT AVAILABLE when no serial exists.')
        def import_equipment():
            src=filedialog.askopenfilename(title='Select Equipment CSV',filetypes=[('CSV Files','*.csv')])
            if not src:return
            try:
                with open(src,'r',encoding='utf-8-sig',newline='') as fh:
                    reader=csv.DictReader(fh); headers={str(x).strip().lower():x for x in (reader.fieldnames or [])}; rows=list(reader)
                def ecol(row,*names):
                    for n in names:
                        if n in headers:return (row.get(headers[n]) or '').strip()
                    return ''
                if not rows:return messagebox.showwarning('Import','CSV contains no data rows.')
                valid=[]; errors=[]; seen=set()
                with connect() as con:
                    for n,row in enumerate(rows,2):
                        client_code=ecol(row,'client id','client code','client'); make=ecol(row,'make','manufacturer'); model=ecol(row,'model'); serial=ecol(row,'serial','serial no','serial number')
                        etype=ecol(row,'type','equipment type'); stock=ecol(row,'stock id','external id'); sold=ecol(row,'sold by us','sold by'); sold_date=ecol(row,'sold date')
                        warranty=ecol(row,'warranty till','warranty up to'); amc=ecol(row,'amc till','amc up to'); location=ecol(row,'location')
                        if not client_code or not make or not model or not serial:errors.append(f'Row {n}: Client ID, Make, Model and Serial are required');continue
                        client=con.execute('SELECT id FROM clients WHERE lower(code)=lower(?)',(client_code,)).fetchone()
                        if not client:errors.append(f'Row {n}: Client ID {client_code} not found');continue
                        key=serial.lower()
                        if key!='not available':
                            if key in seen:errors.append(f'Row {n}: duplicate serial inside CSV');continue
                            seen.add(key)
                            dup=con.execute("SELECT code FROM equipment WHERE lower(serial)=lower(?) AND lower(serial)<>'not available'",(serial,)).fetchone()
                            if dup:errors.append(f"Row {n}: serial already belongs to {dup['code']}");continue
                        valid.append((client['id'],make,model,serial,stock,etype,sold,sold_date,warranty,amc,location))
                summary=f'Rows: {len(rows)}\\nReady to import: {len(valid)}\\nSkipped / invalid: {len(errors)}'
                if errors:summary+='\\n\\nFirst issues:\\n'+'\\n'.join(errors[:8])
                if not valid:return messagebox.showwarning('Import validation',summary)
                if not messagebox.askyesno('Confirm Equipment Import',summary+'\\n\\nImport the validated equipment?'):return
                with connect() as con:
                    for rec in valid:
                        code=next_code('SEQ','equipment')
                        con.execute('INSERT INTO equipment(code,client_id,make,model,serial,stock_id,equipment_type,sold_by,sold_date,warranty_till,amc_till,location,created,modified) VALUES(?,?,?,?,?,?,?,?,?,?,?,?,?,?)',(code,)+rec+(now(),now()))
                audit(self.current_user['username'],'equipment','CSV','IMPORT',f'{len(valid)} imported; {len(errors)} skipped from {Path(src).name}')
                messagebox.showinfo('Import complete',f'{len(valid)} equipment records imported.\\n{len(errors)} rows skipped.')
            except Exception as ex:messagebox.showerror('Equipment import failed',str(ex))
        tk.Button(eqimp,text='Validate & Import Equipment CSV',command=import_equipment,bg=BLUE,fg='white',bd=0,padx=14,pady=7).pack(anchor='w',padx=14,pady=(0,12))
        hist=panel('Backup History','Recent successful backup packages recorded by this installation.')
        with connect() as con: backups=con.execute('SELECT backup_date,filename,status FROM backup_history ORDER BY id DESC LIMIT 5').fetchall()
        for row in backups: tk.Label(hist,text=f"{row['backup_date']}  •  {row['status']}  •  {Path(row['filename']).name}",bg=CARD,fg=MUTED,font=('Segoe UI',8)).pack(anchor='w',padx=14,pady=2)
        if not backups: tk.Label(hist,text='No backup history recorded yet.',bg=CARD,fg=MUTED,font=('Segoe UI',8)).pack(anchor='w',padx=14,pady=(2,10))

    def show_users(self):
        if not self.require('admin'): return
        self.clear()
        h=tk.Frame(self.content,bg='#164F7C',height=38); h.pack(fill='x'); h.pack_propagate(False)
        tk.Label(h,text='Users & Roles',bg='#164F7C',fg='white',font=('Segoe UI',10,'bold')).pack(side='left',padx=14)
        tk.Label(h,text='Access Administration',bg='#164F7C',fg='#DCECF8',font=('Segoe UI',7)).pack(side='left',padx=8)
        body=self.card(self.content); body.pack(fill='both',expand=True,padx=10,pady=8)
        cols=('Username','Display Name','Role','Status'); tree=ttk.Treeview(body,columns=cols,show='headings',height=14)
        for col in cols: tree.heading(col,text=col); tree.column(col,width=190 if col!='Role' else 240,anchor='w')
        tree.pack(fill='both',expand=True,padx=10,pady=(10,6))
        def refresh():
            tree.delete(*tree.get_children())
            with connect() as con: rows=con.execute('SELECT id,username,display_name,role,active FROM users ORDER BY display_name').fetchall()
            for r in rows: tree.insert('', 'end',iid=str(r['id']),values=(r['username'],r['display_name'],r['role'],'Active' if r['active'] else 'Disabled'))
        def edit_user(uid=None):
            row=None
            if uid:
                with connect() as con: row=con.execute('SELECT * FROM users WHERE id=?',(uid,)).fetchone()
            d=tk.Toplevel(self); d.title('User'); d.geometry('470x430'); d.configure(bg=CARD); d.transient(self); d.grab_set()
            vals={}
            for key,label in [('username','Username'),('display_name','Display Name')]:
                tk.Label(d,text=label,bg=CARD,fg=TEXT,font=('Segoe UI',8,'bold')).pack(anchor='w',padx=22,pady=(12,3)); vals[key]=ttk.Entry(d); vals[key].pack(fill='x',padx=22)
            role=tk.StringVar(value=row['role'] if row else 'Service Coordinator')
            tk.Label(d,text='Role',bg=CARD,fg=TEXT,font=('Segoe UI',8,'bold')).pack(anchor='w',padx=22,pady=(12,3)); ttk.Combobox(d,textvariable=role,values=ROLES,state='readonly').pack(fill='x',padx=22)
            active=tk.BooleanVar(value=bool(row['active']) if row else True); tk.Checkbutton(d,text='Active user',variable=active,bg=CARD,fg=TEXT,activebackground=CARD).pack(anchor='w',padx=18,pady=(10,4))
            tk.Label(d,text='Password (leave blank to keep existing)',bg=CARD,fg=TEXT,font=('Segoe UI',8,'bold')).pack(anchor='w',padx=22,pady=(5,3)); password=ttk.Entry(d,show='*'); password.pack(fill='x',padx=22)
            if row: vals['username'].insert(0,row['username']); vals['display_name'].insert(0,row['display_name'])
            def save_user():
                username=vals['username'].get().strip(); name=vals['display_name'].get().strip()
                if not username or not name:return messagebox.showwarning('Required','Username and Display Name are required.',parent=d)
                try:
                    with connect() as con:
                        if row:
                            removing_admin=row['role']=='Administrator' and (role.get()!='Administrator' or not active.get())
                            if removing_admin:
                                admins=con.execute("SELECT COUNT(*) FROM users WHERE role='Administrator' AND active=1 AND id<>?",(uid,)).fetchone()[0]
                                if admins<1: raise ValueError('SERVIX must keep at least one active Administrator.')
                            con.execute('UPDATE users SET username=?,display_name=?,role=?,active=?,modified=? WHERE id=?',(username,name,role.get(),1 if active.get() else 0,now(),uid))
                            if password.get():
                                if len(password.get())<8: raise ValueError('Password must be at least 8 characters.')
                                salt,digest=hash_password(password.get()); con.execute('UPDATE users SET password_salt=?,password_hash=?,must_change_password=1 WHERE id=?',(salt,digest,uid))
                            audit(self.current_user['username'],'user',uid,'UPDATE',f'{username} / {role.get()} / active={active.get()}')
                        else:
                            if len(password.get())<8: raise ValueError('A password of at least 8 characters is required for a new user.')
                            salt,digest=hash_password(password.get())
                            cur=con.execute('INSERT INTO users(username,display_name,role,active,password_salt,password_hash,must_change_password,created,modified) VALUES(?,?,?,?,?,?,1,?,?)',(username,name,role.get(),1 if active.get() else 0,salt,digest,now(),now()))
                            audit(self.current_user['username'],'user',cur.lastrowid,'CREATE',f'{username} / {role.get()}')
                    d.destroy(); refresh()
                except Exception as ex: messagebox.showerror('User not saved',str(ex),parent=d)
            tk.Button(d,text='Save User',command=save_user,bg=BLUE,fg='white',bd=0,padx=16,pady=7).pack(pady=14)
        buttons=tk.Frame(body,bg=CARD); buttons.pack(fill='x',padx=10,pady=(0,10))
        tk.Button(buttons,text='+ New User',command=lambda:edit_user(),bg=BLUE,fg='white',bd=0,padx=13,pady=7).pack(side='left')
        tk.Button(buttons,text='Edit Selected',command=lambda:edit_user(int(tree.selection()[0])) if tree.selection() else None,bg='#EAF2FF',fg=BLUE,bd=0,padx=13,pady=7).pack(side='left',padx=6)
        refresh()

    def show_settings(self):
        if not self.require('admin'): return
        self.clear()
        h=tk.Frame(self.content,bg='#164F7C',height=38); h.pack(fill='x'); h.pack_propagate(False)
        tk.Label(h,text='Administration',bg='#164F7C',fg='white',font=('Segoe UI',10,'bold')).pack(side='left',padx=14)
        tk.Label(h,text='Branding / Identity / Numbering Settings',bg='#164F7C',fg='#DCECF8',font=('Segoe UI',7)).pack(side='left',padx=8)
        brand=self.card(self.content); brand.pack(fill='x',padx=10,pady=(8,6)); brand.grid_columnconfigure((0,1,2),weight=1)
        tk.Label(brand,text='Company Branding / Header',bg=CARD,fg=TEXT,font=('Segoe UI',8,'bold')).grid(row=0,column=0,columnspan=3,sticky='w',padx=14,pady=(12,2))
        tk.Label(brand,text='Change HAC/company identity later without changing application code.',bg=CARD,fg=MUTED,font=('Segoe UI',8)).grid(row=1,column=0,columnspan=3,sticky='w',padx=14,pady=(0,8))
        short=self.form_field(brand,'Header Short Name',2,0); short.insert(0,get_setting('company_short_name','HAC'))
        cname=self.form_field(brand,'Company Name',2,1); cname.insert(0,get_setting('company_name','HAC'))
        stitle=self.form_field(brand,'System Title',2,2); stitle.insert(0,get_setting('system_title','Service Management System'))
        subtitle=self.form_field(brand,'Header Subtitle',4,0); subtitle.insert(0,get_setting('system_subtitle','Service | Calibration | Warranty | AMC'))
        logo=self.form_field(brand,'Logo File (PNG)',4,1); logo.insert(0,get_setting('company_logo_path',''))
        def choose_logo():
            p=filedialog.askopenfilename(filetypes=[('PNG Logo','*.png')])
            if p: logo.delete(0,'end'); logo.insert(0,p)
        tk.Button(brand,text='Choose Logo',command=choose_logo,bg='#EAF2FF',fg=BLUE,bd=0,padx=12,pady=7).grid(row=5,column=1,sticky='e',padx=10,pady=(0,8))
        def save_brand():
            set_setting('company_short_name',short.get().strip() or 'HAC'); set_setting('company_name',cname.get().strip() or short.get().strip() or 'HAC')
            set_setting('system_title',stitle.get().strip() or 'Service Management System'); set_setting('system_subtitle',subtitle.get().strip())
            lp=logo.get().strip()
            if lp and Path(lp).exists():
                from database import DATA_ROOT
                d=DATA_ROOT/'branding'; d.mkdir(parents=True,exist_ok=True); dest=d/'company_logo.png'; shutil.copy2(lp,dest); set_setting('company_logo_path',str(dest))
            elif not lp:set_setting('company_logo_path','')
            messagebox.showinfo('Branding saved','Company/header branding saved. Restart SERVIX to refresh the main header.')
        tk.Button(brand,text='Save Branding',command=save_brand,bg=BLUE,fg='white',bd=0,padx=18,pady=8).grid(row=7,column=2,sticky='e',padx=10,pady=10)

        card=self.card(self.content); card.pack(fill='x',padx=10,pady=(0,10))
        tk.Label(card,text='Service ID Numbering',bg=CARD,fg=TEXT,font=('Segoe UI',8,'bold')).pack(anchor='w',padx=16,pady=(10,4))
        row=tk.Frame(card,bg=CARD); row.pack(fill='x',padx=16,pady=12)
        prefix=ttk.Entry(row,width=10); prefix.insert(0,get_setting('service_prefix','SRV')); prefix.pack(side='left',padx=5)
        start=ttk.Entry(row,width=15); start.insert(0,get_setting('service_start','1')); start.pack(side='left',padx=5)
        digits=ttk.Entry(row,width=8); digits.insert(0,get_setting('service_digits','6')); digits.pack(side='left',padx=5)
        def save_settings():
            try: n=max(1,int(start.get())); d=max(1,int(digits.get()))
            except ValueError: return messagebox.showwarning('Numbering','Starting number and digits must be whole numbers.')
            p=prefix.get().strip().upper()
            if not p: return messagebox.showwarning('Numbering','Prefix cannot be blank.')
            with connect() as con: issued=con.execute('SELECT COUNT(*) FROM services').fetchone()[0]
            old=int(get_setting('service_start','1'))
            if issued and n!=old: return messagebox.showwarning('Protected setting','Service IDs already exist, so the starting number is locked.')
            set_setting('service_prefix',p); set_setting('service_start',n); set_setting('service_digits',d)
            messagebox.showinfo('Saved','Service ID numbering saved.')
        tk.Button(card,text='Save Service ID Numbering',command=save_settings,bg=BLUE,fg='white',bd=0,padx=18,pady=9).pack(anchor='e',padx=16,pady=(0,16))
        auto=self.card(self.content); auto.pack(fill='x',padx=10,pady=(0,10))
        tk.Label(auto,text='Automatic Backup',bg=CARD,fg=TEXT,font=('Segoe UI',8,'bold')).pack(anchor='w',padx=16,pady=(10,4))
        ar=tk.Frame(auto,bg=CARD); ar.pack(fill='x',padx=16,pady=(4,12))
        auto_enabled=tk.BooleanVar(value=get_setting('auto_backup_enabled','1')=='1'); tk.Checkbutton(ar,text='Enable automatic backup when SERVIX starts',variable=auto_enabled,bg=CARD,fg=TEXT).pack(side='left')
        tk.Label(ar,text='Interval days',bg=CARD,fg=MUTED).pack(side='left',padx=(18,4)); auto_days=ttk.Entry(ar,width=6); auto_days.insert(0,get_setting('auto_backup_days','1')); auto_days.pack(side='left')
        tk.Label(ar,text='Keep backups',bg=CARD,fg=MUTED).pack(side='left',padx=(18,4)); auto_keep=ttk.Entry(ar,width=6); auto_keep.insert(0,get_setting('auto_backup_keep','14')); auto_keep.pack(side='left')
        def save_auto():
            try:days=max(1,int(auto_days.get())); keep=max(1,int(auto_keep.get()))
            except ValueError:return messagebox.showwarning('Automatic Backup','Interval and retention must be whole numbers.')
            set_setting('auto_backup_enabled','1' if auto_enabled.get() else '0'); set_setting('auto_backup_days',days); set_setting('auto_backup_keep',keep)
            audit(self.current_user['username'],'settings','automatic_backup','UPDATE',f'enabled={auto_enabled.get()}, days={days}, keep={keep}'); messagebox.showinfo('Saved','Automatic backup settings saved.')
        tk.Button(ar,text='Save',command=save_auto,bg=BLUE,fg='white',bd=0,padx=14,pady=6).pack(side='left',padx=12)
        quality=self.card(self.content); quality.pack(fill='x',padx=10,pady=(0,10))
        tk.Label(quality,text='Data Quality / Repeat Complaint',bg=CARD,fg=TEXT,font=('Segoe UI',8,'bold')).pack(anchor='w',padx=16,pady=(10,4))
        qr=tk.Frame(quality,bg=CARD); qr.pack(fill='x',padx=16,pady=(4,12)); tk.Label(qr,text='Repeat complaint lookback (days)',bg=CARD,fg=MUTED).pack(side='left')
        repeat_days=ttk.Entry(qr,width=8); repeat_days.insert(0,get_setting('repeat_complaint_days','60')); repeat_days.pack(side='left',padx=8)
        def save_quality():
            try: days=max(1,int(repeat_days.get()))
            except ValueError: return messagebox.showwarning('Data Quality','Repeat complaint days must be a whole number.')
            set_setting('repeat_complaint_days',days); audit(self.current_user['username'],'settings','repeat_complaint_days','UPDATE',str(days)); messagebox.showinfo('Saved','Repeat complaint detection window saved.')
        tk.Button(qr,text='Save',command=save_quality,bg=BLUE,fg='white',bd=0,padx=14,pady=6).pack(side='left')

    def global_search(self):
        q=self.search.get().strip()
        if not q or q.startswith('Search Service ID'):return
        self.clear(); self.heading('Search Results',q); like=f'%{q}%'
        tabs=ttk.Notebook(self.content); tabs.pack(fill='both',expand=True,padx=28,pady=(0,22))
        services=tk.Frame(tabs,bg=CARD); clients=tk.Frame(tabs,bg=CARD); equipment=tk.Frame(tabs,bg=CARD)
        tabs.add(services,text=' Service Calls '); tabs.add(clients,text=' Clients '); tabs.add(equipment,text=' Equipment ')
        self.service_tree(services,where='s.code LIKE ? OR c.name LIKE ? OR e.code LIKE ? OR e.serial LIKE ? OR e.make LIKE ? OR e.model LIKE ?',args=(like,like,like,like,like,like))
        ccols=('Client ID','Name','Contact','Mobile','Email','City'); ctr=ttk.Treeview(clients,columns=ccols,show='headings')
        for x in ccols:ctr.heading(x,text=x)
        ctr.pack(fill='both',expand=True,padx=12,pady=12)
        ecols=('SERVIX ID','Client','Make','Model','Serial','Stock / External ID'); etr=ttk.Treeview(equipment,columns=ecols,show='headings')
        for x in ecols:etr.heading(x,text=x)
        etr.pack(fill='both',expand=True,padx=12,pady=12)
        with connect() as con:
            for x in con.execute('SELECT code,name,contact,mobile,email,city FROM clients WHERE code LIKE ? OR name LIKE ? OR mobile LIKE ? OR email LIKE ?',(like,like,like,like)):ctr.insert('','end',values=tuple(x))
            for x in con.execute('''SELECT e.code,c.name,e.make,e.model,e.serial,e.stock_id FROM equipment e LEFT JOIN clients c ON c.id=e.client_id
                                    WHERE e.code LIKE ? OR c.name LIKE ? OR e.make LIKE ? OR e.model LIKE ? OR e.serial LIKE ? OR e.stock_id LIKE ?''',(like,like,like,like,like,like)):etr.insert('','end',values=tuple(x))
        ctr.bind('<Double-1>',lambda e:self.show_client_360(ctr.item(ctr.focus(),'values')[0]) if ctr.focus() else None)
        etr.bind('<Double-1>',lambda e:self.show_equipment_360(etr.item(etr.focus(),'values')[0]) if etr.focus() else None)

if __name__=='__main__': Servix().mainloop()
