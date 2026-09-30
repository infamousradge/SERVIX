import tkinter as tk
from tkinter import ttk, messagebox, filedialog
from pathlib import Path
import csv
import shutil
from database import connect, init_db, next_code, now, today, get_setting, set_setting
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
        self.style.configure('Treeview',font=('Segoe UI',10),rowheight=31,background='white',fieldbackground='white',borderwidth=0)
        self.style.configure('Treeview.Heading',font=('Segoe UI',10,'bold'),background='#EAF1F8',foreground=TEXT,padding=8)
        self.style.map('Treeview',background=[('selected','#D9ECFF')],foreground=[('selected',TEXT)])
        self.style.configure('TEntry',padding=7); self.style.configure('TCombobox',padding=6)
        self.style.configure('TNotebook',background=BG,borderwidth=0)
        self.style.configure('TNotebook.Tab',font=('Segoe UI',9,'bold'),padding=(16,9),background='#EAF1F8',foreground=MUTED)
        self.style.map('TNotebook.Tab',background=[('selected','white')],foreground=[('selected',BLUE)])
        self.page=None; self.build_shell(); self.show_dashboard()

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
        items=[('Dashboard','⌂',self.show_dashboard),('Service Calls','⌕',self.show_services),('Clients','♟',self.show_clients),('Equipment','▣',self.show_equipment),('Warranty & AMC','◆',self.show_warranty),('Engineers','♟',self.show_engineers),('Parts / Inventory','↕',self.show_parts_inventory),('Commercial & Payments','₹',self.show_commercial),('Documents','▧',self.show_documents),('Reports & Analytics','▥',self.show_reports),('Data Export / Import','⇄',self.show_reports),('Administration','⚙',self.show_settings)]
        for label,icon,cmd in items:
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
        uf=tk.Frame(user,bg='#063765'); uf.pack(side='left'); tk.Label(uf,text='Admin',bg='#063765',fg='white',font=('Segoe UI',8,'bold')).pack(anchor='w'); tk.Label(uf,text='Administrator',bg='#063765',fg='#D6E8F7',font=('Segoe UI',6)).pack(anchor='w')
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

    def show_engineers(self): self.simple_summary('Engineers','Engineer workload and service assignment',[('Active Services',self.q1("SELECT COUNT(*) FROM services WHERE engineer!='' AND status NOT IN ('Closed','Cancelled')"),BLUE),('Unassigned',self.q1("SELECT COUNT(*) FROM services WHERE (engineer IS NULL OR engineer='') AND status NOT IN ('Closed','Cancelled')"),ORANGE)])
    def show_parts_inventory(self): self.simple_summary('Parts / Inventory','Parts recorded across service work',[('Parts Entries',self.q1('SELECT COUNT(*) FROM parts'),BLUE),('Chargeable Parts',self.q1("SELECT COUNT(*) FROM parts WHERE chargeable='Chargeable'"),ORANGE)])
    def show_documents(self): self.simple_summary('Documents','Service images, PDFs and certificates',[('Attachments',self.q1('SELECT COUNT(*) FROM attachments'),BLUE),('Calibration Certificates',self.q1("SELECT COUNT(*) FROM calibration WHERE certificate_no!=''"),GREEN)])

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
        self.clear(); self.heading('Create Service Call','Fast office entry • create missing client/equipment here • only genuine essentials block creation')
        form=self.card(self.content); form.pack(fill='x',padx=28,pady=(0,12)); form.grid_columnconfigure((0,1,2),weight=1)

        client=self.form_field(form,'Client',0,0,[],required=True)
        equip=self.form_field(form,'SERVIX Equipment ID',0,1,[],required=True)
        reason=self.form_field(form,'Reason for Service',0,2,['Breakdown / Complaint','Calibration','Preventive Maintenance','AMC Preventive Visit','Installation / Commissioning','Inspection / Check-up','Performance Verification','Software/Firmware Update','Accessory Replacement','Part Replacement','Customer Requested Service','Other'],required=True)
        warranty=self.form_field(form,'Under Warranty?',2,0,['Yes','No'],required=True)
        amc=self.form_field(form,'Under AMC?',2,1,['Yes','No'],required=True)
        engineer=self.form_field(form,'Assigned Engineer (important)',2,2,None)
        priority=self.form_field(form,'Priority',4,0,['Normal','Urgent','Critical']); priority.set('Normal')
        source=self.form_field(form,'Request Source (optional)',4,1,['Phone','Email','WhatsApp','Walk-in','Other'])
        status=self.form_field(form,'Status',4,2,['New','Assigned','Received']); status.set('New')

        cmap={}; emap={}
        def refresh_lists(select_client_id=None,select_equipment_id=None):
            nonlocal cmap,emap
            with connect() as con:
                clients=[(x['id'],f"{x['code']} — {x['name']}") for x in con.execute('SELECT id,code,name FROM clients ORDER BY name')]
                equipment=[(x['id'],x['client_id'],f"{x['code']} — {x['make']} {x['model']} — {x['serial'] or 'Serial not available'}") for x in con.execute('SELECT id,client_id,code,make,model,serial FROM equipment ORDER BY id DESC')]
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

        quick=tk.Frame(form,bg=CARD); quick.grid(row=6,column=0,columnspan=3,sticky='ew',padx=10,pady=(2,8))
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

        tk.Label(form,text='Complaint / Requirement *',bg=CARD,fg=TEXT,font=('Segoe UI',9,'bold')).grid(row=7,column=0,sticky='w',padx=10,pady=(8,3))
        complaint=tk.Text(form,height=5,font=('Segoe UI',10),relief='solid',bd=1); complaint.grid(row=8,column=0,columnspan=3,sticky='ew',padx=10,pady=(0,10))

        guide=self.card(self.content); guide.pack(fill='x',padx=28,pady=(0,10))
        tk.Label(guide,text='* Mandatory   •   Engineer / Priority are important   •   Request Source is optional   •   Quote, charges, payment, work done and dispatch are completed later when relevant.',bg=CARD,fg=MUTED,font=('Segoe UI',8)).pack(anchor='w',padx=14,pady=10)

        actions=tk.Frame(self.content,bg=BG); actions.pack(fill='x',padx=28)
        def save():
            cid=cmap.get(client.get()); eid=emap.get(equip.get()); text=complaint.get('1.0','end').strip()
            if not cid or not eid or not reason.get() or not warranty.get() or not amc.get() or not text:return messagebox.showwarning('Mandatory information','Complete Client, Equipment, Reason, Complaint, Warranty and AMC.')
            with connect() as con:
                owner=con.execute('SELECT client_id FROM equipment WHERE id=?',(eid,)).fetchone()
                if not owner or owner[0]!=cid:return messagebox.showwarning('Equipment mismatch','Selected equipment does not belong to the selected client. Refresh the selection and try again.')
                if reason.get()=='Breakdown / Complaint':
                    serial=con.execute('SELECT serial FROM equipment WHERE id=?',(eid,)).fetchone()[0]
                    prev=con.execute("""SELECT code,opened,complaint FROM services WHERE equipment_id=? AND reason='Breakdown / Complaint'
                                        AND id<>(SELECT COALESCE(MAX(id),0)+1 FROM services) ORDER BY id DESC LIMIT 1""",(eid,)).fetchone()
                    if prev and not messagebox.askyesno('Previous complaint found',f"This device has a previous breakdown: {prev['code']} ({prev['opened']}).\n\nPrevious complaint: {prev['complaint']}\n\nCreate a new Service ID?",parent=self):return
                sc=next_code('SRV','services'); ts=now()
                cur=con.execute('''INSERT INTO services(code,client_id,equipment_id,opened,request_source,reason,complaint,warranty,amc,engineer,priority,status,payment_status,modified)
                                   VALUES(?,?,?,?,?,?,?,?,?,?,?,?,?,?)''',(sc,cid,eid,ts,source.get(),reason.get(),text,warranty.get(),amc.get(),engineer.get().strip(),priority.get() or 'Normal',status.get() or 'New','Not Applicable',ts))
                con.execute('INSERT INTO history(service_id,event_date,note,user) VALUES(?,?,?,?)',(cur.lastrowid,ts,'Service call created from office intake','Office'))
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
        ov.grid_columnconfigure((0,1,2),weight=1); ov.grid_rowconfigure(0,weight=1)
        client_box=tk.LabelFrame(ov,text=' 1. Client Information ',bg=CARD,fg=BLUE,font=('Segoe UI',9,'bold'),highlightthickness=1,highlightbackground='#B8D8F3'); client_box.grid(row=0,column=0,sticky='nsew',padx=(8,4),pady=8)
        equip_box=tk.LabelFrame(ov,text=' 2. Equipment Information ',bg=CARD,fg=BLUE,font=('Segoe UI',9,'bold'),highlightthickness=1,highlightbackground='#B8D8F3'); equip_box.grid(row=0,column=1,sticky='nsew',padx=4,pady=8)
        service_box=tk.LabelFrame(ov,text=' 3. Service Details ',bg=CARD,fg=BLUE,font=('Segoe UI',9,'bold'),highlightthickness=1,highlightbackground='#B8D8F3'); service_box.grid(row=0,column=2,sticky='nsew',padx=(4,8),pady=8)
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
        tech.grid_columnconfigure((0,1,2),weight=1)
        stage=tk.Frame(tech,bg='#F7FAFD',highlightthickness=1,highlightbackground=BORDER); stage.grid(row=-1,column=0,columnspan=3,sticky='ew',padx=10,pady=(10,4))
        tk.Label(stage,text='WORKFLOW CONTROL',bg='#F7FAFD',fg=BLUE,font=('Segoe UI',8,'bold')).pack(side='left',padx=12,pady=8)
        tk.Label(stage,text=f"Current: {r['status']}   •   Complete only the fields required for the stage you are moving to.",bg='#F7FAFD',fg=MUTED,font=('Segoe UI',8)).pack(side='left',padx=8)
        stat=self.form_field(tech,'Status',0,0,['New','Acknowledged','Assigned','Equipment Awaited','Received','Visit Scheduled','Under Diagnosis','Awaiting Customer','Awaiting Approval','Awaiting Parts','Repair in Progress','Testing','Ready for Dispatch','Dispatched','Resolved','Closed','Reopened','Cancelled']); stat.set(r['status'])
        pending=self.form_field(tech,'Pending Reason',0,1,['','Awaiting Customer','Awaiting Parts','Awaiting Approval','Awaiting Payment','Awaiting Engineer','Other']); pending.set(r['pending_reason'] or '')
        eng=self.form_field(tech,'Engineer',0,2); eng.insert(0,r['engineer'] or '')
        received=self.form_field(tech,'Equipment Received Date',2,0); received.insert(0,r['received_date'] or '')
        condition=self.form_field(tech,'Received Condition / Accessories',2,1); condition.insert(0,r['received_condition'] or '')
        work_date=self.form_field(tech,'Engineer Visit / Work Date',2,2); work_date.insert(0,r['work_date'] or '')
        diag=self.form_field(tech,'Diagnosis',4,0); diag.insert(0,r['diagnosis'] or '')
        root=self.form_field(tech,'Root Cause',4,1); root.insert(0,r['root_cause'] or '')
        work=self.form_field(tech,'Work Performed',4,2); work.insert(0,r['work_done'] or '')
        testing=self.form_field(tech,'Testing / Verification',6,0); testing.insert(0,r['testing_result'] or '')
        result=self.form_field(tech,'Final Result',6,1,['Pending','Successful','Partially Resolved','Not Resolved']); result.set(r['final_result'] or 'Pending')
        next_action=self.form_field(tech,'Next Action',6,2); next_action.insert(0,r['next_action'] or '')
        dispatch=self.form_field(tech,'Dispatch Date',8,0); dispatch.insert(0,r['dispatch_date'] or '')
        dispatch_mode=self.form_field(tech,'Dispatch Mode',8,1,['','Courier','Hand','Other']); dispatch_mode.set(r['dispatch_mode'] or '')
        dispatch_ref=self.form_field(tech,'Dispatch Reference / Remarks',8,2); dispatch_ref.insert(0,r['dispatch_reference'] or '')
        completion=self.form_field(tech,'Service Completion Date',10,0); completion.insert(0,r['completion_date'] or '')
        closure=self.form_field(tech,'Closure Date',10,1); closure.insert(0,r['closure_date'] or '')
        cancel_reason=self.form_field(tech,'Cancel / Reopen Reason',10,2); cancel_reason.insert(0,r['cancel_reason'] or '')

        update_box=tk.LabelFrame(tech,text=' Add chronological engineer / office update ',bg=CARD,fg=TEXT,font=('Segoe UI',9,'bold'))
        update_box.grid(row=12,column=0,columnspan=3,sticky='ew',padx=10,pady=10); update_box.grid_columnconfigure((0,1,2),weight=1)
        upd_type=self.form_field(update_box,'Update Type',0,0,['Engineer Update','Technical','Customer Communication','Follow-up','Management']); upd_type.set('Engineer Update')
        upd_date=self.form_field(update_box,'Date / Time',0,1); upd_date.insert(0,now())
        upd_eng=self.form_field(update_box,'Engineer',0,2); upd_eng.insert(0,r['engineer'] or '')
        upd_diag=self.form_field(update_box,'Diagnosis / Update',2,0); upd_work=self.form_field(update_box,'Work Done',2,1); upd_next=self.form_field(update_box,'Next Action',2,2)
        def add_update():
            if not upd_date.get().strip() or not (upd_diag.get().strip() or upd_work.get().strip()):return messagebox.showwarning('Update required','Enter the update date/time and Diagnosis/Update or Work Done.')
            with connect() as con:
                con.execute('''INSERT INTO service_updates(service_id,update_date,engineer,update_type,diagnosis,work_done,result,next_action,user) VALUES(?,?,?,?,?,?,?,?,?)''',(r['id'],upd_date.get().strip(),upd_eng.get().strip(),upd_type.get(),upd_diag.get().strip(),upd_work.get().strip(),result.get(),upd_next.get().strip(),'Office'))
                con.execute('INSERT INTO history(service_id,event_date,note,user) VALUES(?,?,?,?)',(r['id'],now(),f"{upd_type.get()}: {upd_work.get().strip() or upd_diag.get().strip()}",'Office'))
                con.execute('UPDATE services SET modified=? WHERE id=?',(now(),r['id']))
            self.show_service_detail(code)
        tk.Button(update_box,text='+ Add Update',command=add_update,bg='#EAF2FF',fg=BLUE,bd=0,padx=15,pady=8).grid(row=4,column=2,sticky='e',padx=10,pady=10)

        ucols=('Date','Type','Engineer','Diagnosis / Update','Work Done','Next Action'); utr=ttk.Treeview(tech,columns=ucols,show='headings',height=6)
        for x in ucols:utr.heading(x,text=x)
        utr.grid(row=14,column=0,columnspan=3,sticky='nsew',padx=10,pady=8)
        with connect() as con:
            for x in con.execute('SELECT update_date,update_type,engineer,diagnosis,work_done,next_action FROM service_updates WHERE service_id=? ORDER BY id DESC',(r['id'],)):utr.insert('','end',values=tuple(x))

        def save_tech():
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

        # Parts: office entry only; add rows as the engineer reports work.
        pcols=('Part No.','Description','Qty','FOC / Chargeable','Amount','Remarks'); ptr=ttk.Treeview(parts_tab,columns=pcols,show='headings',height=10)
        for pc in pcols: ptr.heading(pc,text=pc)
        ptr.pack(fill='both',expand=True,padx=12,pady=(12,6))
        pform=tk.Frame(parts_tab,bg=CARD); pform.pack(fill='x',padx=12,pady=8)
        pent={}
        for i,(key,label,width) in enumerate([('no','Part No.',14),('desc','Description',28),('qty','Qty',8),('amount','Amount',10),('remarks','Remarks',22)]):
            tk.Label(pform,text=label,bg=CARD,fg=MUTED,font=('Segoe UI',8)).grid(row=0,column=i,sticky='w',padx=4)
            pent[key]=ttk.Entry(pform,width=width); pent[key].grid(row=1,column=i,padx=4,sticky='ew')
        pcharge=ttk.Combobox(pform,width=15,state='readonly',values=['FOC','Chargeable']); pcharge.set('Chargeable'); pcharge.grid(row=1,column=5,padx=4)
        def refresh_parts():
            for x in ptr.get_children(): ptr.delete(x)
            with connect() as con:
                for x in con.execute('SELECT part_no,description,qty,chargeable,amount,remarks FROM parts WHERE service_id=? ORDER BY id DESC',(r['id'],)): ptr.insert('','end',values=tuple(x))
        def save_part():
            try: qty=float(pent['qty'].get() or 1); amount=float(pent['amount'].get() or 0)
            except ValueError: return messagebox.showwarning('Check values','Quantity and amount must be numeric.')
            if not pent['desc'].get().strip(): return messagebox.showwarning('Required','Part description is required.')
            add_part(r['id'],pent['no'].get(),pent['desc'].get(),qty,pcharge.get(),amount,pent['remarks'].get())
            add_history(r['id'],f"Part recorded: {pent['desc'].get()} x {qty}")
            for x in pent.values(): x.delete(0,'end')
            refresh_parts()
        tk.Button(pform,text='+ Add Part',command=save_part,bg=BLUE,fg='white',bd=0,padx=14,pady=8).grid(row=1,column=6,padx=8)
        refresh_parts()

        # Calibration fields only matter when the service reason is Calibration.
        cal_tab.grid_columnconfigure((0,1),weight=1)
        cal_date=self.form_field(cal_tab,'Calibration Date',0,0); cal_result=self.form_field(cal_tab,'Result',0,1,['Pass','Fail'])
        cert=self.form_field(cal_tab,'Certificate No.',2,0); next_due=self.form_field(cal_tab,'Next Due Date',2,1); cal_remarks=self.form_field(cal_tab,'Remarks',4,0)
        with connect() as con: cr=con.execute('SELECT * FROM calibration WHERE service_id=?',(r['id'],)).fetchone()
        if cr:
            cal_date.insert(0,cr['calibration_date'] or ''); cal_result.set(cr['result'] or ''); cert.insert(0,cr['certificate_no'] or ''); next_due.insert(0,cr['next_due'] or ''); cal_remarks.insert(0,cr['remarks'] or '')
        def save_cal():
            if r['reason']=='Calibration' and (not cal_date.get() or not cal_result.get()): return messagebox.showwarning('Required','Calibration Date and Result are required for calibration jobs.')
            upsert_calibration(r['id'],cal_date.get(),cal_result.get(),cert.get(),next_due.get(),cal_remarks.get()); add_history(r['id'],f"Calibration updated: {cal_result.get() or 'details saved'}"); messagebox.showinfo('Saved','Calibration information saved.')
        tk.Button(cal_tab,text='Save Calibration',command=save_cal,bg=BLUE,fg='white',bd=0,padx=18,pady=9).grid(row=6,column=1,sticky='e',padx=10,pady=15)
        if r['reason']!='Calibration': tk.Label(cal_tab,text='This service is not marked as Calibration. These fields are optional.',bg=CARD,fg=MUTED).grid(row=7,column=0,columnspan=2,pady=8)

        # Images are resized/compressed. PDFs remain lossless/readable.
        acols=('Document','Type','Original','Stored','Saved'); atr=ttk.Treeview(att_tab,columns=acols,show='headings')
        for ac in acols: atr.heading(ac,text=ac)
        atr.pack(fill='both',expand=True,padx=12,pady=(12,6))
        def human(n):
            n=float(n or 0)
            for unit in ('B','KB','MB','GB'):
                if n<1024:return f'{n:.0f} {unit}' if unit=='B' else f'{n:.1f} {unit}'
                n/=1024
            return f'{n:.1f} TB'
        def refresh_att():
            for x in atr.get_children(): atr.delete(x)
            with connect() as con:
                for x in con.execute('SELECT original_name,kind,original_size,stored_size,created FROM attachments WHERE service_id=? ORDER BY id DESC',(r['id'],)): atr.insert('','end',values=(x['original_name'],x['kind'],human(x['original_size']),human(x['stored_size']),x['created']))
        def attach():
            path=filedialog.askopenfilename(filetypes=[('Images / PDF','*.jpg *.jpeg *.png *.webp *.pdf'),('All files','*.*')])
            if not path:return
            try: meta=store_attachment(path,code)
            except Exception as ex:return messagebox.showerror('Attachment',str(ex))
            add_attachment(r['id'],meta); add_history(r['id'],f"Attachment added: {meta['original_name']}"); refresh_att()
        tk.Button(att_tab,text='+ Attach Image / PDF',command=attach,bg=BLUE,fg='white',bd=0,padx=18,pady=9).pack(anchor='e',padx=12,pady=(0,12)); refresh_att()

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
        self.clear(); self.heading('Clients','Client database created naturally from service activity')
        card=self.card(self.content); card.pack(fill='both',expand=True,padx=28,pady=(0,22)); cols=('Client ID','Name','Contact','Mobile','Email','City'); tr=ttk.Treeview(card,columns=cols,show='headings'); [tr.heading(c,text=c) for c in cols]; tr.pack(fill='both',expand=True,padx=12,pady=12)
        with connect() as con:
            for r in con.execute('SELECT code,name,contact,mobile,email,city FROM clients ORDER BY id DESC'):tr.insert('','end',values=tuple(r))
        tk.Button(card,text='+ Add Client',bg=BLUE,fg='white',bd=0,padx=15,pady=8,command=self.client_dialog).place(relx=1,rely=0,x=-20,y=20,anchor='ne')
        tr.bind('<Double-1>',lambda e:self.show_client_360(tr.item(tr.focus(),'values')[0]) if tr.focus() else None)

    def show_client_360(self,code):
        self.clear()
        with connect() as con:
            r=con.execute('SELECT * FROM clients WHERE code=?',(code,)).fetchone()
            if not r:return
            eq=con.execute('SELECT * FROM equipment WHERE client_id=? ORDER BY id DESC',(r['id'],)).fetchall()
            svc=con.execute('''SELECT s.code,s.opened,e.code equipment,e.make,e.model,e.serial,s.reason,s.status,s.warranty,s.amc,s.foc_chargeable,s.payment_status
                               FROM services s LEFT JOIN equipment e ON e.id=s.equipment_id WHERE s.client_id=? ORDER BY s.id DESC''',(r['id'],)).fetchall()
        self.heading(f"{r['code']} — {r['name']}",'Client 360 • contacts, equipment and complete service activity')
        metrics=tk.Frame(self.content,bg=BG); metrics.pack(fill='x',padx=22)
        self.metric(metrics,'Equipment',len(eq),BLUE); self.metric(metrics,'Total Services',len(svc),GREEN)
        self.metric(metrics,'Open Calls',sum(1 for x in svc if x['status'] not in ('Closed','Cancelled')),ORANGE)
        self.metric(metrics,'Payment Pending',sum(1 for x in svc if x['payment_status'] in ('Pending','Part Paid')),RED)
        info=self.card(self.content); info.pack(fill='x',padx=28,pady=14)
        details=[('Contact',r['contact']),('Mobile',r['mobile']),('Email',r['email']),('City',r['city']),('Address',r['address'])]
        for i,(k,v) in enumerate(details):
            tk.Label(info,text=k,bg=CARD,fg=MUTED,font=('Segoe UI',8)).grid(row=0,column=i,sticky='w',padx=12,pady=(10,2))
            tk.Label(info,text=v or '—',bg=CARD,fg=TEXT,font=('Segoe UI',9,'bold')).grid(row=1,column=i,sticky='w',padx=12,pady=(0,10))
            info.grid_columnconfigure(i,weight=1)
        tabs=ttk.Notebook(self.content); tabs.pack(fill='both',expand=True,padx=28,pady=(0,22))
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
        self.clear(); self.heading('Equipment','Permanent SERVIX identity for every serviced device')
        card=self.card(self.content); card.pack(fill='both',expand=True,padx=28,pady=(0,22)); cols=('SERVIX ID','Client','Make','Model','Serial','Stock / External ID','Warranty Till','AMC Till'); tr=ttk.Treeview(card,columns=cols,show='headings'); [tr.heading(c,text=c) for c in cols]; tr.pack(fill='both',expand=True,padx=12,pady=12)
        with connect() as con:
            for r in con.execute('SELECT e.code,c.name,e.make,e.model,e.serial,e.stock_id,e.warranty_till,e.amc_till FROM equipment e LEFT JOIN clients c ON c.id=e.client_id ORDER BY e.id DESC'):tr.insert('','end',values=tuple(r))
        tk.Button(card,text='+ Add Equipment',bg=BLUE,fg='white',bd=0,padx=15,pady=8,command=self.equipment_dialog).place(relx=1,rely=0,x=-20,y=20,anchor='ne')
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
        self.heading(r['code'],f"{r['make']} {r['model']} • S/N {r['serial'] or 'Not available'} • Device 360")
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
        self.clear(); self.heading('Warranty & AMC','Equipment coverage and upcoming expiry alerts')
        metrics=tk.Frame(self.content,bg=BG); metrics.pack(fill='x',padx=22)
        self.metric(metrics,'Warranty Expiring',self.q1("SELECT COUNT(*) FROM equipment WHERE warranty_till!='' AND date(warranty_till)>=date('now') AND date(warranty_till)<=date('now','+30 day')"),ORANGE,'Next 30 days')
        self.metric(metrics,'AMC Expiring',self.q1("SELECT COUNT(*) FROM equipment WHERE amc_till!='' AND date(amc_till)>=date('now') AND date(amc_till)<=date('now','+30 day')"),BLUE,'Next 30 days')
        self.metric(metrics,'Warranty Expired',self.q1("SELECT COUNT(*) FROM equipment WHERE warranty_till!='' AND date(warranty_till)<date('now')"),RED,'Equipment master')
        self.metric(metrics,'AMC Expired',self.q1("SELECT COUNT(*) FROM equipment WHERE amc_till!='' AND date(amc_till)<date('now')"),RED,'Equipment master')
        card=self.card(self.content); card.pack(fill='both',expand=True,padx=28,pady=18)
        tk.Label(card,text='Coverage Register',font=('Segoe UI',13,'bold'),bg=CARD,fg=TEXT).pack(anchor='w',padx=14,pady=(14,6))
        cols=('SERVIX ID','Client','Make','Model','Serial','Warranty Till','AMC Till','Location'); tr=ttk.Treeview(card,columns=cols,show='headings')
        for x,w in zip(cols,[115,210,120,150,130,115,115,160]):tr.heading(x,text=x); tr.column(x,width=w,anchor='w')
        tr.pack(fill='both',expand=True,padx=14,pady=(4,14))
        with connect() as con:
            for r in con.execute('''SELECT e.code,c.name,e.make,e.model,e.serial,e.warranty_till,e.amc_till,e.location FROM equipment e LEFT JOIN clients c ON c.id=e.client_id
                                    WHERE (e.warranty_till IS NOT NULL AND e.warranty_till!='') OR (e.amc_till IS NOT NULL AND e.amc_till!='')
                                    ORDER BY CASE WHEN e.amc_till='' OR e.amc_till IS NULL THEN e.warranty_till ELSE e.amc_till END'''):tr.insert('','end',values=tuple(r))
        tr.bind('<Double-1>',lambda e:self.show_equipment_360(tr.item(tr.focus(),'values')[0]) if tr.focus() else None)
    def show_calibration(self):
        self.clear(); self.heading('Calibration Control','Due dates, overdue certificates and complete calibration service history')
        metrics=tk.Frame(self.content,bg=BG); metrics.pack(fill='x',padx=22)
        self.metric(metrics,'Open Jobs',self.q1("SELECT COUNT(*) FROM services WHERE reason='Calibration' AND status NOT IN ('Closed','Cancelled')"),BLUE,'Active calibration work')
        self.metric(metrics,'Due in 30 Days',self.q1("SELECT COUNT(*) FROM calibration WHERE next_due!='' AND date(next_due)>=date('now') AND date(next_due)<=date('now','+30 day')"),ORANGE,'Plan customer follow-up')
        self.metric(metrics,'Overdue',self.q1("SELECT COUNT(*) FROM calibration WHERE next_due!='' AND date(next_due)<date('now')"),RED,'Requires attention')
        self.metric(metrics,'Passed',self.q1("SELECT COUNT(*) FROM calibration WHERE result='Pass'"),GREEN,'Recorded calibration results')
        card=self.card(self.content); card.pack(fill='both',expand=True,padx=28,pady=18)
        head=tk.Frame(card,bg=CARD); head.pack(fill='x',padx=14,pady=(12,4))
        tk.Label(head,text='Calibration Register',font=('Segoe UI',13,'bold'),bg=CARD,fg=TEXT).pack(side='left')
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
        flt.bind('<<ComboboxSelected>>',load); load()
        tr.bind('<Double-1>',lambda e:self.show_service_detail(tr.item(tr.focus(),'values')[0]) if tr.focus() else None)

    def show_commercial(self):self.simple_summary('Commercial & Payments','Quotation, verbal discussion, FOC/chargeable and payment tracking',[('Payment Pending',self.q1("SELECT COUNT(*) FROM services WHERE payment_status='Pending'"),RED),('Paid',self.q1("SELECT COUNT(*) FROM services WHERE payment_status='Paid'"),GREEN),('FOC',self.q1("SELECT COUNT(*) FROM services WHERE foc_chargeable='FOC'"),BLUE),('Chargeable',self.q1("SELECT COUNT(*) FROM services WHERE foc_chargeable='Chargeable'"),ORANGE)])

    def show_reports(self):
        self.clear(); self.heading('Reports & Analytics','Operational filters, management totals and export-ready service data')
        filters=self.card(self.content); filters.pack(fill='x',padx=28,pady=(0,12))
        bar=tk.Frame(filters,bg=CARD); bar.pack(fill='x',padx=14,pady=12)
        tk.Label(bar,text='From',bg=CARD,fg=MUTED).pack(side='left'); from_e=ttk.Entry(bar,width=12); from_e.pack(side='left',padx=(5,12))
        tk.Label(bar,text='To',bg=CARD,fg=MUTED).pack(side='left'); to_e=ttk.Entry(bar,width=12); to_e.pack(side='left',padx=(5,12))
        tk.Label(bar,text='Status',bg=CARD,fg=MUTED).pack(side='left'); status=ttk.Combobox(bar,state='readonly',width=17,values=['All','Open','Closed','Awaiting Parts','Awaiting Customer','Dispatched']); status.set('All'); status.pack(side='left',padx=(5,12))
        tk.Label(bar,text='Coverage',bg=CARD,fg=MUTED).pack(side='left'); coverage=ttk.Combobox(bar,state='readonly',width=15,values=['All','Warranty','AMC','OOW','FOC','Chargeable']); coverage.set('All'); coverage.pack(side='left',padx=(5,12))
        tk.Label(bar,text='Reason',bg=CARD,fg=MUTED).pack(side='left'); reason=ttk.Combobox(bar,state='readonly',width=18,values=['All','Breakdown / Complaint','Calibration','Preventive Maintenance','AMC Preventive Visit','Installation / Commissioning','Inspection / Check-up']); reason.set('All'); reason.pack(side='left',padx=(5,8))

        metrics=tk.Frame(self.content,bg=BG); metrics.pack(fill='x',padx=22,pady=(0,12))
        cards=[]
        for title,accent in [('Records',BLUE),('Open',ORANGE),('Closed',GREEN),('Outstanding ₹',RED)]: cards.append(self.metric(metrics,title,'-',accent,'Current filter'))

        table=self.card(self.content); table.pack(fill='both',expand=True,padx=28,pady=(0,12))
        top=tk.Frame(table,bg=CARD); top.pack(fill='x',padx=14,pady=(12,4)); tk.Label(top,text='Service Report',bg=CARD,fg=TEXT,font=('Segoe UI',13,'bold')).pack(side='left')
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

    def show_settings(self):
        brand=self.card(self.content); brand.pack(fill='x',padx=28,pady=(0,12)); brand.grid_columnconfigure((0,1,2),weight=1)
        tk.Label(brand,text='Company Branding / Header',bg=CARD,fg=TEXT,font=('Segoe UI',12,'bold')).grid(row=0,column=0,columnspan=3,sticky='w',padx=14,pady=(12,2))
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

        self.clear(); self.heading('Administration - Settings','Configure Service ID numbering before go-live')
        card=self.card(self.content); card.pack(fill='x',padx=28,pady=(0,16))
        tk.Label(card,text='Service ID Numbering',bg=CARD,fg=TEXT,font=('Segoe UI',13,'bold')).pack(anchor='w',padx=16,pady=(14,4))
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
