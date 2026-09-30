from pathlib import Path
from reportlab.lib import colors
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.enums import TA_CENTER
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle
from reportlab.lib.units import mm

def _s(v): return str(v or '—')
def create_service_report(path, service, client, equipment, parts, calibration, company):
    path=Path(path); styles=getSampleStyleSheet()
    body=ParagraphStyle('body',parent=styles['BodyText'],fontSize=8,leading=11)
    title=ParagraphStyle('title',parent=styles['Title'],fontSize=16,textColor=colors.HexColor('#164F7C'),alignment=TA_CENTER)
    section=ParagraphStyle('section',parent=styles['Heading3'],fontSize=9,textColor=colors.white,backColor=colors.HexColor('#164F7C'),spaceBefore=7,spaceAfter=5,leftIndent=4,leading=15)
    doc=SimpleDocTemplate(str(path),pagesize=A4,rightMargin=12*mm,leftMargin=12*mm,topMargin=11*mm,bottomMargin=11*mm,title='Service Report '+_s(service['code']))
    story=[Paragraph(_s(company.get('name')),title),Paragraph(_s(company.get('title')),ParagraphStyle('sub',parent=body,alignment=TA_CENTER,textColor=colors.HexColor('#6E7B8D'))),Spacer(1,5)]
    def info(name,rows):
        story.append(Paragraph(name,section)); data=[]
        for a,b,c,d in rows:data.append([Paragraph('<b>'+a+'</b>',body),Paragraph(_s(b),body),Paragraph('<b>'+c+'</b>',body),Paragraph(_s(d),body)])
        t=Table(data,colWidths=[30*mm,63*mm,30*mm,63*mm]); t.setStyle(TableStyle([('GRID',(0,0),(-1,-1),.35,colors.HexColor('#C8D9E8')),('BACKGROUND',(0,0),(0,-1),colors.HexColor('#F3F7FB')),('BACKGROUND',(2,0),(2,-1),colors.HexColor('#F3F7FB')),('VALIGN',(0,0),(-1,-1),'TOP'),('PADDING',(0,0),(-1,-1),4)])); story.append(t)
    info('SERVICE INFORMATION',[('Service ID',service['code'],'Status',service['status']),('Opened',service['opened'],'Reason',service['reason']),('Priority',service['priority'],'Engineer',service['engineer']),('Warranty',service['warranty'],'AMC',service['amc'])])
    info('CLIENT & EQUIPMENT',[('Client ID',client['code'],'Client',client['name']),('Contact',client['contact'],'Mobile',client['mobile']),('Equipment ID',equipment['code'],'Make / Model',_s(equipment['make'])+' / '+_s(equipment['model'])),('Serial No.',equipment['serial'],'Equipment Type',equipment['equipment_type'])])
    story.append(Paragraph('COMPLAINT / REQUIREMENT',section)); story.append(Paragraph(_s(service['complaint']),body))
    story.append(Paragraph('TECHNICAL WORK',section))
    for label,key in [('Diagnosis','diagnosis'),('Work Performed','work_done'),('Testing / Verification','testing_result'),('Final Result','final_result')]: story += [Paragraph('<b>'+label+':</b> '+_s(service[key]),body),Spacer(1,3)]
    if parts:
        story.append(Paragraph('PARTS USED',section)); pdata=[['Part No.','Description','Qty','Category','Amount']]+[[_s(x['part_no']),_s(x['description']),_s(x['qty']),_s(x['chargeable']),_s(x['amount'])] for x in parts]
        pt=Table(pdata,colWidths=[30*mm,75*mm,18*mm,30*mm,25*mm]); pt.setStyle(TableStyle([('BACKGROUND',(0,0),(-1,0),colors.HexColor('#EAF4FF')),('GRID',(0,0),(-1,-1),.35,colors.HexColor('#C8D9E8')),('FONTNAME',(0,0),(-1,0),'Helvetica-Bold'),('FONTSIZE',(0,0),(-1,-1),7)])); story.append(pt)
    if calibration: info('CALIBRATION',[('Calibration Date',calibration['calibration_date'],'Result',calibration['result']),('Certificate No.',calibration['certificate_no'],'Certificate Date',calibration['certificate_date']),('Next Calibration Due',calibration['next_due'],'Performed By',calibration['performed_by']),('Standards / Reference',calibration['standards_reference'],'Remarks',calibration['remarks'])])
    info('COMPLETION & DISPATCH',[('Completion Date',service['completion_date'],'Closure Date',service['closure_date']),('Dispatch Date',service['dispatch_date'],'Dispatch Mode',service['dispatch_mode']),('Dispatch Reference',service['dispatch_reference'],'Service Category',service['foc_chargeable'])])
    story += [Spacer(1,12),Table([['Engineer / Service Signature','Customer Acknowledgement'],['\n\n____________________________','\n\n____________________________']],colWidths=[90*mm,90*mm],style=[('ALIGN',(0,0),(-1,-1),'CENTER'),('FONTNAME',(0,0),(-1,0),'Helvetica-Bold'),('FONTSIZE',(0,0),(-1,-1),8)])]
    doc.build(story); return path
