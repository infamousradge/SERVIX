import tkinter as tk
from tkinter import ttk, messagebox, filedialog
from pathlib import Path
import csv
from database import connect, init_db, next_code, now, today
from attachment_utils import store_attachment
from service_repository import add_history, add_part, upsert_calibration, add_attachment

ROOT=Path(__file__).resolve().parent
NAVY='#071A3D'; NAVY2='#0C2B5B'; BLUE='#0876D1'; CYAN='#11B6D8'; GREEN='#48C774'; BG='#F3F7FB'; CARD='#FFFFFF'; TEXT='#142033'; MUTED='#6E7B8D'; BORDER='#DDE6F0'; RED='#D9534F'; ORANGE='#F0A23B'

class Servix(tk.Tk):
    def __init__(self):
        super().__init__(); init_db()
        self.title('SERVIX — Service Management'); self.geometry('1480x900'); self.minsize(1180,720); self.configure(bg=BG)
        self.style=ttk.Style(self); self.style.theme_use('clam')
        self.style.configure('Treeview',font=('Segoe UI',10),rowheight=31,background='white',fieldbackground='white',borderwidth=0)
        self.style.configure('Treeview.Heading',font=('Segoe UI',10,'bold'),background='#EAF1F8',foreground=TEXT,padding=8)
        self.style.map('Treeview',background=[('selected','#D9ECFF')],foreground=[('selected',TEXT)])
        self.style.configure('TEntry',padding=7); self.style.configure('TCombobox',padding=6)
        self.page=None; self.build_shell(); self.show_dashboard()

    def build_shell(self):
        self.sidebar=tk.Frame(self,bg=NAVY,width=235); self.sidebar.pack(side='left',fill='y'); self.sidebar.pack_propagate(False)
        brand=tk.Frame(self.sidebar,bg=NAVY,height=110); brand.pack(fill='x'); brand.pack_propagate(False)
        tk.Label(brand,text='⚙',font=('Segoe UI Symbol',31),bg=NAVY,fg=CYAN).pack(side='left',padx=(18,7))
        b=tk.Frame(brand,bg=NAVY); b.pack(side='left',pady=22); tk.Label(b,text='SERVIX',font=('Segoe UI',22,'bold'),bg=NAVY,fg='white').pack(anchor='w'); tk.Label(b,text='SERVICE MANAGEMENT',font=('Segoe UI',7),bg=NAVY,fg='#8EDFE8').pack(anchor='w')
        self.nav={}
        items=[('Dashboard','▦',self.show_dashboard),('Service Calls','☷',self.show_services),('New Service','＋',self.show_new_service),('Clients','♙',self.show_clients),('Equipment','⚙',self.show_equipment),('Warranty & AMC','◇',self.show_warranty),('Calibration','◎',self.show_calibration),('Commercial','₹',self.show_commercial),('Reports & Export','▥',self.show_reports)]
        for label,icon,cmd in items:
            btn=tk.Button(self.sidebar,text=f'  {icon}   {label}',font=('Segoe UI',10),anchor='w',bd=0,relief='flat',bg=NAVY,fg='#DDE9F7',activebackground=NAVY2,activeforeground='white',cursor='hand2',command=lambda l=label,c=cmd:self.go(l,c)); btn.pack(fill='x',padx=10,pady=2,ipady=9); self.nav[label]=btn
        tk.Label(self.sidebar,text='SERVIX V1 • LOCAL DATABASE',font=('Segoe UI',7),bg=NAVY,fg='#7790B0').pack(side='bottom',pady=16)
        right=tk.Frame(self,bg=BG); right.pack(side='left',fill='both',expand=True)
        top=tk.Frame(right,bg='white',height=70,highlightthickness=1,highlightbackground=BORDER); top.pack(fill='x'); top.pack_propagate(False)
        self.search=tk.Entry(top,font=('Segoe UI',10),bd=0,bg='#F2F6FA',fg=TEXT,insertbackground=TEXT); self.search.insert(0,'Search Service ID, Client, Serial, SERVIX Equipment ID…'); self.search.pack(side='left',fill='x',expand=True,padx=24,pady=16,ipady=9); self.search.bind('<Return>',lambda e:self.global_search())
        tk.Button(top,text='Search',command=self.global_search,bg=BLUE,fg='white',bd=0,font=('Segoe UI',9,'bold'),padx=18,pady=8).pack(side='left',padx=(0,14))
        tk.Label(top,text='Office User',bg='white',fg=TEXT,font=('Segoe UI',9,'bold')).pack(side='right',padx=20)
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

    def show_dashboard(self):
        self.clear(); self.heading('Dashboard','Service operations at a glance',self.show_new_service,'+ New Service Call')
        row=tk.Frame(self.content,bg=BG); row.pack(fill='x',padx=22)
        self.metric(row,'Open Service Calls',self.q1("SELECT COUNT(*) FROM services WHERE status NOT IN ('Closed','Cancelled')"),BLUE,'Active workload')
        self.metric(row,'Awaiting Action',self.q1("SELECT COUNT(*) FROM services WHERE status IN ('Awaiting Customer','Awaiting Approval','Awaiting Parts')"),ORANGE,'Customer / approval / parts')
        self.metric(row,'Payment Pending',self.q1("SELECT COUNT(*) FROM services WHERE payment_status IN ('Pending','Part Paid')"),RED,'Commercial follow-up')
        self.metric(row,'Calibration',self.q1("SELECT COUNT(*) FROM services WHERE reason='Calibration' AND status!='Closed'"),GREEN,'Open calibration jobs')
        lower=tk.Frame(self.content,bg=BG); lower.pack(fill='both',expand=True,padx=28,pady=18)
        recent=self.card(lower); recent.pack(side='left',fill='both',expand=True,padx=(0,9)); tk.Label(recent,text='Recent Service Calls',font=('Segoe UI',13,'bold'),bg=CARD,fg=TEXT).pack(anchor='w',padx=18,pady=15); self.service_tree(recent,8)
        side=self.card(lower); side.pack(side='left',fill='y',padx=(9,0)); tk.Label(side,text='Quick Assessment',font=('Segoe UI',13,'bold'),bg=CARD,fg=TEXT).pack(anchor='w',padx=18,pady=15)
        for label,sql in [('Warranty Calls',"warranty='Yes'"),('AMC Calls',"amc='Yes'"),('Chargeable',"foc_chargeable='Chargeable'"),('FOC',"foc_chargeable='FOC'"),('Dispatched',"status='Dispatched'")]:
            r=tk.Frame(side,bg=CARD); r.pack(fill='x',padx=18,pady=7); tk.Label(r,text=label,bg=CARD,fg=MUTED,font=('Segoe UI',9)).pack(side='left'); tk.Label(r,text=str(self.q1('SELECT COUNT(*) FROM services WHERE '+sql)),bg=CARD,fg=TEXT,font=('Segoe UI',12,'bold')).pack(side='right')

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
        self.clear(); self.heading('Create Service Call','Only essential information is mandatory at opening')
        form=self.card(self.content); form.pack(fill='x',padx=28,pady=(0,18)); form.grid_columnconfigure((0,1,2),weight=1)
        with connect() as con:
            clients=[(r['id'],f"{r['code']} — {r['name']}") for r in con.execute('SELECT id,code,name FROM clients ORDER BY name')]; eq=[(r['id'],f"{r['code']} — {r['make']} {r['model']} — {r['serial'] or 'No S/N'}") for r in con.execute('SELECT id,code,make,model,serial FROM equipment ORDER BY id DESC')]
        cmap={v:k for k,v in clients}; emap={v:k for k,v in eq}
        client=self.form_field(form,'Client',0,0,list(cmap),required=True); equip=self.form_field(form,'SERVIX Equipment ID',0,1,list(emap),required=True); reason=self.form_field(form,'Reason for Service',0,2,['Breakdown / Complaint','Calibration','Preventive Maintenance','AMC Preventive Visit','Installation / Commissioning','Inspection / Check-up','Performance Verification','Software/Firmware Update','Part Replacement','Other'],required=True)
        warranty=self.form_field(form,'Under Warranty?',2,0,['Yes','No'],required=True); amc=self.form_field(form,'Under AMC?',2,1,['Yes','No'],required=True); engineer=self.form_field(form,'Assigned Engineer',2,2,None)
        priority=self.form_field(form,'Priority',4,0,['Normal','Urgent','Critical']); priority.set('Normal'); source=self.form_field(form,'Request Source',4,1,['Phone','Email (manual entry)','WhatsApp','Walk-in','Engineer Update','Other']); status=self.form_field(form,'Status',4,2,['New','Assigned','Received']); status.set('New')
        tk.Label(form,text='Complaint / Requirement *',bg=CARD,fg=TEXT,font=('Segoe UI',9,'bold')).grid(row=6,column=0,sticky='w',padx=10,pady=(8,3)); complaint=tk.Text(form,height=5,font=('Segoe UI',10),relief='solid',bd=1); complaint.grid(row=7,column=0,columnspan=3,sticky='ew',padx=10,pady=(0,10))
        actions=tk.Frame(self.content,bg=BG); actions.pack(fill='x',padx=28)
        def save():
            if not client.get() or not equip.get() or not reason.get() or not warranty.get() or not amc.get() or not complaint.get('1.0','end').strip(): return messagebox.showwarning('Mandatory information','Please complete all fields marked *.')
            sc=next_code('SRV','services'); ts=now()
            with connect() as con:
                cur=con.execute('''INSERT INTO services(code,client_id,equipment_id,opened,request_source,reason,complaint,warranty,amc,engineer,priority,status,payment_status,modified) VALUES(?,?,?,?,?,?,?,?,?,?,?,?,?,?)''',(sc,cmap[client.get()],emap[equip.get()],ts,source.get(),reason.get(),complaint.get('1.0','end').strip(),warranty.get(),amc.get(),engineer.get(),priority.get() or 'Normal',status.get() or 'New','Not Applicable',ts)); con.execute('INSERT INTO history(service_id,event_date,note,user) VALUES(?,?,?,?)',(cur.lastrowid,ts,'Service call created','Office'))
            messagebox.showinfo('Service created',f'{sc} created successfully.'); self.show_service_detail(sc)
        tk.Button(actions,text='Create Service ID',command=save,bg=BLUE,fg='white',font=('Segoe UI',10,'bold'),bd=0,padx=22,pady=11).pack(side='right')

    def show_service_detail(self,code):
        self.clear()
        with connect() as con:r=con.execute('''SELECT s.*,c.name client,e.code equipment,e.make,e.model,e.serial FROM services s LEFT JOIN clients c ON c.id=s.client_id LEFT JOIN equipment e ON e.id=s.equipment_id WHERE s.code=?''',(code,)).fetchone()
        if not r:return
        self.heading(code,f"{r['client']} • {r['equipment']} • {r['make']} {r['model']} • S/N {r['serial'] or 'Not available'}")
        tabs=ttk.Notebook(self.content); tabs.pack(fill='both',expand=True,padx=28,pady=(0,22))
        ov=tk.Frame(tabs,bg=CARD); tech=tk.Frame(tabs,bg=CARD); parts_tab=tk.Frame(tabs,bg=CARD); cal_tab=tk.Frame(tabs,bg=CARD); att_tab=tk.Frame(tabs,bg=CARD); comm=tk.Frame(tabs,bg=CARD); hist=tk.Frame(tabs,bg=CARD)
        tabs.add(ov,text=' Overview '); tabs.add(tech,text=' Technical '); tabs.add(parts_tab,text=' Parts '); tabs.add(cal_tab,text=' Calibration '); tabs.add(att_tab,text=' Attachments '); tabs.add(comm,text=' Commercial '); tabs.add(hist,text=' History ')
        for i,(k,v) in enumerate([('Status',r['status']),('Reason',r['reason']),('Warranty',r['warranty']),('AMC',r['amc']),('Engineer',r['engineer'] or '—'),('Priority',r['priority']),('Opened',r['opened']),('Received',r['received_date'] or '—')]):
            c=self.card(ov); c.grid(row=i//4,column=i%4,sticky='nsew',padx=8,pady=8); ov.grid_columnconfigure(i%4,weight=1); tk.Label(c,text=k,bg=CARD,fg=MUTED,font=('Segoe UI',8)).pack(anchor='w',padx=12,pady=(9,2)); tk.Label(c,text=str(v),bg=CARD,fg=TEXT,font=('Segoe UI',10,'bold')).pack(anchor='w',padx=12,pady=(0,9))
        tk.Label(ov,text='Complaint / Requirement',bg=CARD,fg=TEXT,font=('Segoe UI',10,'bold')).grid(row=2,column=0,columnspan=4,sticky='w',padx=10,pady=(15,3)); t=tk.Text(ov,height=5,font=('Segoe UI',10)); t.grid(row=3,column=0,columnspan=4,sticky='ew',padx=10); t.insert('1.0',r['complaint']); t.configure(state='disabled')
        tech.grid_columnconfigure((0,1),weight=1); diag=self.form_field(tech,'Diagnosis / Assessment',0,0); work=self.form_field(tech,'Work Done',0,1); result=self.form_field(tech,'Final Result',2,0,['Pending','Successful','Partially Resolved','Not Resolved']); stat=self.form_field(tech,'Status',2,1,['New','Assigned','Received','Under Diagnosis','Awaiting Customer','Awaiting Approval','Awaiting Parts','Repair in Progress','Testing','Ready for Dispatch','Dispatched','Closed']); stat.set(r['status']); received=self.form_field(tech,'Equipment Received Date',4,0); received.insert(0,r['received_date'] or ''); dispatch=self.form_field(tech,'Dispatch Date',4,1); dispatch.insert(0,r['dispatch_date'] or ''); diag.insert(0,r['diagnosis'] or ''); work.insert(0,r['work_done'] or ''); result.set(r['final_result'] or 'Pending')
        def save_tech():
            with connect() as con:
                con.execute('UPDATE services SET diagnosis=?,work_done=?,final_result=?,status=?,received_date=?,dispatch_date=?,modified=? WHERE code=?',(diag.get(),work.get(),result.get(),stat.get(),received.get(),dispatch.get(),now(),code)); sid=con.execute('SELECT id FROM services WHERE code=?',(code,)).fetchone()[0]; con.execute('INSERT INTO history(service_id,event_date,note,user) VALUES(?,?,?,?)',(sid,now(),f"Office update: {stat.get()} — {work.get() or diag.get() or 'record updated'}",'Office'))
            messagebox.showinfo('Saved','Technical update saved.'); self.show_service_detail(code)
        tk.Button(tech,text='Save Technical Update',command=save_tech,bg=BLUE,fg='white',bd=0,padx=18,pady=9).grid(row=6,column=1,sticky='e',padx=10,pady=15)
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

        comm.grid_columnconfigure((0,1,2),weight=1); foc=self.form_field(comm,'FOC / Chargeable',0,0,['FOC','Chargeable']); foc.set(r['foc_chargeable'] or ''); quote=self.form_field(comm,'Quotation Status',0,1,['Quotation Sent','No Quotation — Verbal Discussion','Estimate Shared by Phone','Quotation Not Required','Pending Decision']); quote.set(r['quote_status'] or ''); pay=self.form_field(comm,'Payment Status',0,2,['Not Applicable','Pending','Part Paid','Paid']); pay.set(r['payment_status'] or 'Not Applicable'); svc=self.form_field(comm,'Service Charge',2,0); svc.insert(0,str(r['service_charge'] or '')); parts=self.form_field(comm,'Parts Charge',2,1); parts.insert(0,str(r['parts_charge'] or '')); qa=self.form_field(comm,'Quote Amount',2,2); qa.insert(0,str(r['quote_amount'] or ''))
        def save_comm():
            def num(x):
                try:return float(x or 0)
                except:return 0
            with connect() as con:con.execute('UPDATE services SET foc_chargeable=?,quote_status=?,payment_status=?,service_charge=?,parts_charge=?,quote_amount=?,modified=? WHERE code=?',(foc.get(),quote.get(),pay.get(),num(svc.get()),num(parts.get()),num(qa.get()),now(),code))
            messagebox.showinfo('Saved','Commercial information saved.')
        tk.Button(comm,text='Save Commercial Update',command=save_comm,bg=BLUE,fg='white',bd=0,padx=18,pady=9).grid(row=4,column=2,sticky='e',padx=10,pady=15)
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
    def client_dialog(self):
        d=tk.Toplevel(self); d.title('Add Client'); d.geometry('560x520'); d.configure(bg=CARD); vals={}; specs=[('name','Client / Company',True),('contact','Contact Person',False),('mobile','Mobile',False),('email','Email',False),('address','Address',False),('city','City',False),('notes','Notes',False)]
        for i,(k,l,req) in enumerate(specs):tk.Label(d,text=l+(' *' if req else ''),bg=CARD,fg=TEXT,font=('Segoe UI',9,'bold')).pack(anchor='w',padx=25,pady=(10,2)); vals[k]=ttk.Entry(d); vals[k].pack(fill='x',padx=25)
        def save():
            if not vals['name'].get() or (not vals['mobile'].get() and not vals['email'].get()):return messagebox.showwarning('Required','Client name and at least Mobile or Email are required.',parent=d)
            with connect() as con:
                dup=con.execute('SELECT code,name FROM clients WHERE (mobile<>"" AND mobile=?) OR (email<>"" AND email=?)',(vals['mobile'].get(),vals['email'].get())).fetchone()
                if dup and not messagebox.askyesno('Possible duplicate',f"Possible duplicate: {dup['code']} — {dup['name']}\nCreate anyway?",parent=d):return
                ts=now(); con.execute('INSERT INTO clients(code,name,contact,mobile,email,address,city,notes,created,modified) VALUES(?,?,?,?,?,?,?,?,?,?)',(next_code('CLI','clients'),*[vals[k].get() for k in ('name','contact','mobile','email','address','city','notes')],ts,ts))
            d.destroy(); self.show_clients()
        tk.Button(d,text='Save Client',command=save,bg=BLUE,fg='white',bd=0,padx=18,pady=9).pack(pady=20)

    def show_equipment(self):
        self.clear(); self.heading('Equipment','Permanent SERVIX identity for every serviced device')
        card=self.card(self.content); card.pack(fill='both',expand=True,padx=28,pady=(0,22)); cols=('SERVIX ID','Client','Make','Model','Serial','Stock / External ID','Warranty Till','AMC Till'); tr=ttk.Treeview(card,columns=cols,show='headings'); [tr.heading(c,text=c) for c in cols]; tr.pack(fill='both',expand=True,padx=12,pady=12)
        with connect() as con:
            for r in con.execute('SELECT e.code,c.name,e.make,e.model,e.serial,e.stock_id,e.warranty_till,e.amc_till FROM equipment e LEFT JOIN clients c ON c.id=e.client_id ORDER BY e.id DESC'):tr.insert('','end',values=tuple(r))
        tk.Button(card,text='+ Add Equipment',bg=BLUE,fg='white',bd=0,padx=15,pady=8,command=self.equipment_dialog).place(relx=1,rely=0,x=-20,y=20,anchor='ne')
    def equipment_dialog(self):
        d=tk.Toplevel(self); d.title('Add Equipment'); d.geometry('650x650'); d.configure(bg=CARD)
        with connect() as con:clients=[(r['id'],f"{r['code']} — {r['name']}") for r in con.execute('SELECT id,code,name FROM clients ORDER BY name')]
        cmap={v:k for k,v in clients}; vals={}; specs=[('client','Client',list(cmap)),('make','Make',None),('model','Model',None),('serial','Serial Number',None),('stock','Stock / External Equipment ID',None),('type','Equipment Type',None),('sold','Sold By',['Us','Other','Unknown']),('warranty','Warranty Till',None),('amc','AMC Till',None),('location','Location / Department',None)]
        for k,l,v in specs:tk.Label(d,text=l+(' *' if k in ('client','make','model') else ''),bg=CARD,fg=TEXT,font=('Segoe UI',9,'bold')).pack(anchor='w',padx=25,pady=(7,2)); w=ttk.Combobox(d,values=v,state='readonly') if v is not None else ttk.Entry(d); w.pack(fill='x',padx=25); vals[k]=w
        def save():
            if not vals['client'].get() or not vals['make'].get() or not vals['model'].get():return messagebox.showwarning('Required','Client, Make and Model are mandatory.',parent=d)
            with connect() as con:
                if vals['serial'].get():
                    dup=con.execute('SELECT code FROM equipment WHERE serial=?',(vals['serial'].get(),)).fetchone()
                    if dup and not messagebox.askyesno('Possible duplicate',f"Serial already exists as {dup['code']}. Create anyway?",parent=d):return
                ts=now(); con.execute('''INSERT INTO equipment(code,client_id,make,model,serial,stock_id,equipment_type,sold_by,warranty_till,amc_till,location,created,modified) VALUES(?,?,?,?,?,?,?,?,?,?,?,?,?)''',(next_code('SEQ','equipment'),cmap[vals['client'].get()],vals['make'].get(),vals['model'].get(),vals['serial'].get(),vals['stock'].get(),vals['type'].get(),vals['sold'].get(),vals['warranty'].get(),vals['amc'].get(),vals['location'].get(),ts,ts))
            d.destroy(); self.show_equipment()
        tk.Button(d,text='Save Equipment',command=save,bg=BLUE,fg='white',bd=0,padx=18,pady=9).pack(pady=18)

    def simple_summary(self,title,subtitle,rows):
        self.clear(); self.heading(title,subtitle); holder=tk.Frame(self.content,bg=BG); holder.pack(fill='x',padx=22)
        for name,val,color in rows:self.metric(holder,name,val,color)
        box=self.card(self.content); box.pack(fill='both',expand=True,padx=28,pady=18); tk.Label(box,text='Use Service Calls and Equipment records for detailed entries. More dedicated controls will be added in the next build.',bg=CARD,fg=MUTED,font=('Segoe UI',10)).pack(pady=35)
    def show_warranty(self):self.simple_summary('Warranty & AMC','Simple coverage overview',[('Under Warranty',self.q1("SELECT COUNT(*) FROM services WHERE warranty='Yes'"),GREEN),('Under AMC',self.q1("SELECT COUNT(*) FROM services WHERE amc='Yes'"),BLUE),('Out of Warranty',self.q1("SELECT COUNT(*) FROM services WHERE warranty='No'"),ORANGE)])
    def show_calibration(self):self.simple_summary('Calibration','Calibration jobs are separated from breakdown history',[('Open Calibration',self.q1("SELECT COUNT(*) FROM services WHERE reason='Calibration' AND status!='Closed'"),BLUE),('Completed',self.q1("SELECT COUNT(*) FROM services WHERE reason='Calibration' AND status='Closed'"),GREEN)])
    def show_commercial(self):self.simple_summary('Commercial & Payments','Quotation, verbal discussion, FOC/chargeable and payment tracking',[('Payment Pending',self.q1("SELECT COUNT(*) FROM services WHERE payment_status='Pending'"),RED),('Paid',self.q1("SELECT COUNT(*) FROM services WHERE payment_status='Paid'"),GREEN),('FOC',self.q1("SELECT COUNT(*) FROM services WHERE foc_chargeable='FOC'"),BLUE),('Chargeable',self.q1("SELECT COUNT(*) FROM services WHERE foc_chargeable='Chargeable'"),ORANGE)])

    def show_reports(self):
        self.clear(); self.heading('Reports & Export','Filter data and export for reporting or migration')
        box=self.card(self.content); box.pack(fill='x',padx=28,pady=(0,18)); tk.Label(box,text='Service CSV Export',bg=CARD,fg=TEXT,font=('Segoe UI',13,'bold')).pack(anchor='w',padx=18,pady=(16,5)); tk.Label(box,text='Exports the complete service dataset currently stored in SERVIX. Date/filter controls will expand in the next build.',bg=CARD,fg=MUTED).pack(anchor='w',padx=18)
        def export():
            path=filedialog.asksaveasfilename(defaultextension='.csv',filetypes=[('CSV','*.csv')],initialfile='SERVIX_Service_Export.csv');
            if not path:return
            with connect() as con:
                rows=con.execute('''SELECT s.code,s.opened,c.name,e.code,e.make,e.model,e.serial,s.reason,s.complaint,s.warranty,s.amc,s.engineer,s.priority,s.status,s.diagnosis,s.work_done,s.final_result,s.foc_chargeable,s.service_charge,s.parts_charge,s.quote_status,s.payment_status,s.dispatch_date FROM services s LEFT JOIN clients c ON c.id=s.client_id LEFT JOIN equipment e ON e.id=s.equipment_id ORDER BY s.id''').fetchall()
            headers=['Service ID','Opened','Client','SERVIX Equipment ID','Make','Model','Serial','Reason','Complaint','Warranty','AMC','Engineer','Priority','Status','Diagnosis','Work Done','Final Result','FOC/Chargeable','Service Charge','Parts Charge','Quotation','Payment','Dispatch']
            with open(path,'w',newline='',encoding='utf-8-sig') as f:w=csv.writer(f); w.writerow(headers); w.writerows([tuple(x) for x in rows])
            messagebox.showinfo('Export complete',f'{len(rows)} service records exported.')
        tk.Button(box,text='Export Service Data to CSV',command=export,bg=BLUE,fg='white',bd=0,padx=18,pady=9).pack(anchor='w',padx=18,pady=16)

    def global_search(self):
        q=self.search.get().strip()
        if not q or q.startswith('Search Service ID'):return
        self.clear(); self.heading('Search Results',q); box=self.card(self.content); box.pack(fill='both',expand=True,padx=28,pady=(0,22)); like=f'%{q}%'; self.service_tree(box,where='s.code LIKE ? OR c.name LIKE ? OR e.code LIKE ? OR e.serial LIKE ? OR e.make LIKE ? OR e.model LIKE ?',args=(like,like,like,like,like,like))

if __name__=='__main__': Servix().mainloop()
