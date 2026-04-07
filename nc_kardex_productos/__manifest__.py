# Author: NICA-CREATOR desde Nicaragua 
# Copyright 2021 

{
    'name': 'Kardex for product',
    'version': '18.0.1.1.1',
    'price': 60.00,
    'currency':'USD',
    'support':'gtnorw@yahoo.com',   
    'category': 'Reporting',
    'summary': 'Kardex Report in Excel and  pdf Format, so display the records of products in a table',   
    'author': 'NICA-CREATOR', 
    "depends": ["base", "stock", "account",],
    'images': ['static/description/main_screenshot.png'],
    'data': ['kardex.xml',"karde_report.xml","security/ir.model.access.csv","kardex_dependiente.xml","karde_report_dependiente.xml"],
    'installable': True,
    'application': True,
    'auto_install': True,
    'license': 'OPL-1',
}


# 'data': ['kardex.xml',"karde_report.xml","security/ir.model.access.csv","kardex_dependiente.xml","karde_report_dependiente.xml",],