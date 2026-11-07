"""Synthetic source evidence and the same review API used by the manager UI."""
from PIL import Image,ImageDraw
from app.review import mark_row_reviewed,mark_sheet_approved


def approve_sheet(sheet,folder,tag='sample'):
    source = folder/(tag+'.png')
    image = Image.new('RGB',(958,1350),'white')
    ImageDraw.Draw(image).text((20,20),tag+' '+sheet.employee,fill='black')
    image.save(source)
    sheet.source = str(source)+'#page1'
    sheet.archived_hash = ''
    for row in range(14):
        mark_row_reviewed(sheet,row)
    mark_sheet_approved(sheet)
    return sheet
