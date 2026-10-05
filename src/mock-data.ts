const browserMock: DashboardData = {
  services: [
    {id:1,serviceId:'SRV-24881',openedDate:'2026-10-05',client:'City Hospital',equipment:'MAICO MA42',make:'MAICO',model:'MA42',serialNumber:'123456',reason:'Repair',complaint:'No sound from right ear channel.',engineer:'Rohit',status:'In Progress',priority:'Normal',serviceLocation:'Onsite',dueDate:'2026-10-10',coverage:'Out of Coverage',foc:false,quoteStatus:'Quote Sent',paymentStatus:'Pending',lastUpdated:'2026-10-05 11:38'},
    {id:2,serviceId:'SRV-24880',openedDate:'2026-10-05',client:'Sunrise Clinic',equipment:'Tympanometer',make:'PATH',model:'Sentiero Desktop',serialNumber:'780012',reason:'Calibration',complaint:'Annual calibration due.',engineer:'Amit',status:'Open',priority:'Normal',serviceLocation:'Workshop',dueDate:'2026-10-12',coverage:'AMC',foc:true,quoteStatus:'No Quote',paymentStatus:'Paid',lastUpdated:'2026-10-05 10:54'},
    {id:3,serviceId:'SRV-24879',openedDate:'2026-10-04',client:'ABC Hospital',equipment:'Audiometer',make:'Interacoustics',model:'AC40',serialNumber:'456789',reason:'Repair',complaint:'Intermittent output.',engineer:'Rohan',status:'Pending',priority:'Urgent',serviceLocation:'Workshop',dueDate:'2026-10-06',coverage:'Warranty',foc:true,quoteStatus:'No Quote',paymentStatus:'Pending',lastUpdated:'2026-10-05 09:20'},
    {id:4,serviceId:'SRV-24878',openedDate:'2026-10-03',client:'Life Care',equipment:'Impedance Audiometer',make:'MAICO',model:'MI44',serialNumber:'112233',reason:'Preventive Service',complaint:'Routine service.',engineer:'Rohit',status:'Closed',priority:'Normal',serviceLocation:'Workshop',dueDate:'2026-10-05',coverage:'AMC',foc:false,quoteStatus:'Quote Sent',paymentStatus:'Paid',lastUpdated:'2026-10-05 08:00'},
    {id:5,serviceId:'SRV-24877',openedDate:'2026-09-28',client:'Global Hospital',equipment:'OAE Screener',make:'PATH',model:'Sentiero Screening',serialNumber:'998877',reason:'Repair',complaint:'Probe check fails.',engineer:'Amit',status:'Open',priority:'Urgent',serviceLocation:'Onsite',dueDate:'2026-10-02',coverage:'Out of Coverage',foc:false,quoteStatus:'Quote Sent',paymentStatus:'Pending',lastUpdated:'2026-10-04 17:30'}
  ],
  intake: [
    {id:1,receivedAt:'Today 11:20 AM',client:'City Hospital',contact:'Mr. Sharma',mobile:'9876543210',email:'service@cityhospital.in',equipment:'Audiometer',make:'MAICO',model:'MA42',serialNumber:'123456',complaint:'No sound from right ear.',matchSummary:'Existing Client + Equipment',matchTone:'good',status:'New'},
    {id:2,receivedAt:'Today 10:48 AM',client:'Sunrise Clinic',contact:'Dr. Mehta',mobile:'9876500011',email:'admin@sunriseclinic.in',equipment:'Tympanometer',make:'PATH',model:'Sentiero Desktop',serialNumber:'780012',complaint:'Calibration required.',matchSummary:'Existing Client',matchTone:'good',status:'New'},
    {id:3,receivedAt:'Today 09:15 AM',client:'New Sound Centre',contact:'Ms. Riya',mobile:'9811100022',email:'riya@newsound.in',equipment:'Audiometer',make:'MAICO',model:'MA42',serialNumber:'NS-2201',complaint:'Intermittent issue.',matchSummary:'New Client',matchTone:'neutral',status:'Reviewed'},
    {id:4,receivedAt:'Yesterday 04:20 PM',client:'Global Hospital',contact:'Mr. Khan',mobile:'9822200033',email:'biomed@global.in',equipment:'OAE Screener',make:'PATH',model:'Sentiero Screening',serialNumber:'998877',complaint:'Probe check fails.',matchSummary:'Possible duplicate open call',matchTone:'warn',status:'Duplicate'}
  ],
  clients: [
    {id:1,code:'CLI-00241',name:'City Hospital',contact:'Mr. Sharma',mobile:'9876543210',email:'service@cityhospital.in',city:'New Delhi',state:'Delhi',active:true,serviceCount:24,equipmentCount:8},
    {id:2,code:'CLI-00182',name:'ABC Hospital',contact:'Ms. Kaur',mobile:'9899001100',email:'biomed@abchospital.in',city:'Gurugram',state:'Haryana',active:true,serviceCount:18,equipmentCount:6},
    {id:3,code:'CLI-00202',name:'Sunrise Clinic',contact:'Dr. Mehta',mobile:'9876500011',email:'admin@sunriseclinic.in',city:'Noida',state:'Uttar Pradesh',active:true,serviceCount:12,equipmentCount:4}
  ],
  equipment: [
    {id:1,servixEquipmentId:'EQ-10081',client:'City Hospital',make:'MAICO',model:'MA42',serialNumber:'123456',type:'Audiometer',location:'Audiology Dept.',coverage:'Out of Coverage',serviceCount:3,lastService:'2026-10-05'},
    {id:2,servixEquipmentId:'EQ-10082',client:'Sunrise Clinic',make:'PATH',model:'Sentiero Desktop',serialNumber:'780012',type:'Tympanometer',location:'ENT Dept.',coverage:'AMC',serviceCount:2,lastService:'2026-10-05'},
    {id:3,servixEquipmentId:'EQ-10042',client:'ABC Hospital',make:'Interacoustics',model:'AC40',serialNumber:'456789',type:'Audiometer',location:'Audiology Lab',coverage:'Warranty',serviceCount:5,lastService:'2026-10-04'}
  ],
  partUsage: [
    {id:1,date:'2026-10-05',serviceId:'SRV-24881',client:'City Hospital',equipment:'MAICO MA42',itemName:'Receiver Assembly',make:'MAICO',model:'MA42',partNumber:'RX-120',quantity:1,remarks:'Replaced right receiver'},
    {id:2,date:'2026-10-04',serviceId:'SRV-24879',client:'ABC Hospital',equipment:'AC40',itemName:'Transducer',make:'Interacoustics',model:'TDH39',partNumber:'TD-39',quantity:1,remarks:'Output verification'},
    {id:3,date:'2026-10-03',serviceId:'SRV-24878',client:'Life Care',equipment:'MI44',itemName:'Cable',make:'Generic',model:'USB A-B',partNumber:'CAB-USB',quantity:2,remarks:'Replaced worn cables'},
    {id:4,date:'2026-09-30',serviceId:'SRV-24865',client:'City Hospital',equipment:'MAICO MA42',itemName:'Receiver Assembly',make:'MAICO',model:'MA42',partNumber:'RX-120',quantity:1,remarks:''}
  ],
  users:[
    {id:1,username:'admin',displayName:'Administrator',role:'Administrator',active:true},
    {id:2,username:'office',displayName:'Office Desk',role:'Office User',active:true}
  ],
  sync:{configured:true,lastSuccessfulSync:'2026-10-05 10:45',lastAttemptedSync:'2026-10-05 10:45',newCount:2,status:'up-to-date',message:'Google Form intake is up to date.'}
};
