# -*- coding: utf-8 -*-

import os
#from pyreportjasper import PyReportJasper
from ast import Attribute
from odoo import models, fields, api, SUPERUSER_ID, _
import odoo.addons.decimal_precision as dp
from odoo import tools
from odoo.tools.safe_eval import safe_eval
from odoo.tools import pycompat
from odoo.tools import DEFAULT_SERVER_DATETIME_FORMAT
from odoo.tools import float_is_zero
import datetime 
from datetime import datetime
from datetime import datetime, date, time, timedelta
import calendar

from dateutil.relativedelta import relativedelta
import xlsxwriter

from io import BytesIO
from pytz import timezone
import pytz

from odoo.exceptions import UserError, ValidationError, RedirectWarning
from datetime import datetime, timezone
import pytz
from pytz import timezone as pytz_timezone


from odoo.tools.misc import xlwt
import io
import base64
from base64 import b64encode
from xlwt import easyxf

#import xml.etree.cElementTree as ET
import xml.etree.ElementTree as ET
from datetime import datetime
from pytz import timezone



class kardex_add_user(models.Model):
    _inherit = 'res.company'     
    ver_costo= fields.Boolean(string='Admin', help="Allows the user to see the cost")  
    hide_menu_report_kardex = fields.Many2one('ir.ui.menu',string='hide menu report kardex')  
    encabezado_reporte=fields.Text(string='Encabezado reporte')    
    usuarios_restr = fields.Many2many(comodel_name='res.users',string='Usuarios restringidos', inverse_name='obj_kardex_company')

   


class kardex_add_user(models.Model):
    _inherit = 'res.users'   
    # obj_kardex_company = fields.Many2one('res.company')
        
    def write(self, vals):
        res = super(kardex_add_user, self).write(vals)
        self.self.clear_caches()
        return res

class Menu(models.Model):
    _inherit = 'ir.ui.menu'

    @api.model
    def _visible_menu_ids(self, debug=False):
        menus = super()._visible_menu_ids(debug)

        user = self.env.user
        company = user.company_id

        menu = company.hide_menu_report_kardex
        usuarios = company.usuarios_restr

        if menu and user in usuarios:
            menus.discard(menu.id)

        return menus


class kardex_productos_inventario(models.TransientModel):
    _name = 'kardex.productos.mov'
    _description = "kardex productos"

    # def __init__(self):
    #    if  self.env.user.ver_costo == True :  
    #         raise ValidationError('Tax id is minor than allowed partner')


    @api.model
    def get_default_date_model(self):
        return pytz.UTC.localize(datetime.now()).astimezone(timezone(self.env.user.tz or 'UTC'))

    @api.model
    def _get_from_date(self):
        company = self.env.user.company_id
        current_date = datetime.date.today()
        from_date = company.compute_fiscalyear_dates(current_date)['date_from']
        return from_date
    @api.model
    def _poner_fecha(self): 
        return fields.Datetime.now
            


    @api.model
    def _poner_revos(self):       
        fecha_actual= pytz.timezone('America/Managua')
        return  fecha_actual

    # @api.model
    # def _ver_compos_costos(self): 
    #     if  self.env.user.ver_costo == True :  
    #       poner="administrador"
    #     if  self.env.user.ver_costo == False :    
    #       poner="dependiente"  
    #     return  poner
   
    # @api.model
    # def _poner_fecha2(self):       
    #     fecha_actual2=pytz.UTC.localize(datetime.datetime.now()).astimezone(timezone(self.env.user.tz))
    #     return  fecha_actual2
 
    # ver_campos_costo= fields.Char(string='Ver costo',default=_ver_compos_costos)
    excel_binary = fields.Binary('Field')
    file_name = fields.Char('Report_Name', readonly=True)
    #codigo_barra = fields.Char('Barcode', readonly=True)
    product = fields.Many2one('product.product', string='Product')
    grupo_producto=fields.Many2many('product.category',string='Grupos',help="Add Group products")
    grupo_location=fields.Many2many('stock.location',string='Grupos_location',help="Add Group of location")
    company = fields.Many2one('res.company', required=True, default=lambda self: self.env.user.company_id,
                              string='Current Company')

    ubicacion = fields.Many2one('stock.location', domain=[('usage', '=', "internal")], string='Location')

    date_from = fields.Date(string='Date from',default=fields.Datetime.now)
    date_to = fields.Date(string='Date to', default=fields.Datetime.now)
    #revisio = fields.Char(string='revision', default=lambda self:self.env.user.tz)
    revisio = fields.Char(string='revision',default=_poner_fecha )
    cantidad_inicial = fields.Float('Cuantity Ini:', readonly=True)
    costo_promedio_inicial = fields.Float('Cost  Ini:', readonly=True)
    costo_total_inicial = fields.Float('Cost Total Ini:', readonly=True)

    cantidad_final = fields.Float('Quantity End :', readonly=True)
    costo_promedio = fields.Float('Cost End:', readonly=True)
    costo_total = fields.Float('Costo Total End', readonly=True)

    aplica = fields.Selection([('todas', 'All '), ('ubicacion', 'By location')], required=True, default='todas',
                              string='Selection location')
    select_product = fields.Selection([('todas', 'All Porducts'), ('products', 'By Products')], required=True, default='todas',
                              string='Selection Products')                          

    currency_id = fields.Many2one('res.currency', string='Company currency', required=True,
                                  default=lambda self: self.env.user.company_id.currency_id, readonly=True)

    obj_kardex = fields.One2many(comodel_name='kardex.productos.mov.detalle', inverse_name='obj_kardex_mostrarmovi')

  

    # def _tree_elem(self, ):
    #     root = ET.Element( ' ?xml version="1.0" encoding="UTF-8" standalone="yes"? ')
    #     doc = ET.SubElement(root, "doc")
    #     nodo1 = ET.SubElement(doc, "nodo1", name="nodo")
    #     nodo1.text = "Texto de nodo1"
    #     ET.SubElement(doc, "nodo2", atributo="algo").text = "texto 2"
    #     arbol = ET.ElementTree(root)
    #     arbol.write("C:/Users/pc/Desktop/Programas utilizados/prueba.xml")

        
    def _action_imprimir_grupo_inventario_excel(self, ):
       
        
        self.cantidad_final=0
        self.costo_promedio_inicial=0
        self.costo_total_inicial=0
        self.cantidad_final=0
        self.costo_promedio=0
        self.costo_total=0

        workbook = xlwt.Workbook()
        column_heading = easyxf('font:height 200;font:bold True;')
        column_heading_style = easyxf('font:height 200;font:bold True;pattern: pattern solid, fore_colour grey25')
        worksheet = workbook.add_sheet('Kardex report')
        date_format = xlwt.XFStyle()
        date_format.num_format_str = 'dd/mm/yyyy'
    


        

        number_format = xlwt.XFStyle()
        number_format.num_format_str = '#,##0.00'

        # Ponemos los primeros encabezados
        worksheet.write(0, 0, _('Kardex report product for Group'), column_heading)

        cant_prod=0
        for  grupos  in self.grupo_producto :
        #Vamos agrupando por grupo de productos     
            query_grupos = """
        ---------agrupar productos
select pp.default_code,pp.id,pt.name ->> 'en_US'as name,pt.categ_id  from product_product  pp
inner join product_template  pt on  pp.product_tmpl_id=pt.id
where pt.categ_id = %s
    """
            query_grupos_param = (grupos.id,)
            self.env.cr.execute(query_grupos,query_grupos_param)
            g = self.env.cr.dictfetchall()
         
            conteo = 0
            for prod in g:
                cant_prod+=1
                #Obtenemos la siguiente fila
                if cant_prod == 1:
                  conteo = 0
                if cant_prod > 1 :  
                    query_lineconteo = """
                    select * from kardex_productos_inventario_conteo order by id  asc
                        """
                
                    self.env.cr.execute(query_lineconteo,)
                    conteo_fila = self.env.cr.dictfetchall()
                    for cont in conteo_fila:
                       conteo = cont['detalle_conteo']

                #Repasamos producto por producto    
                worksheet.write(1 + conteo, 0, "Date from:", column_heading_style)
                worksheet.write(1 + conteo, 1, self.date_from, date_format)
                worksheet.write(2 + conteo, 0, "Date to:", column_heading_style)
                worksheet.write(2 + conteo, 1, self.date_to, date_format)
                worksheet.write(1 + conteo, 2, "Product:", column_heading_style)               
                worksheet.write(1 + conteo, 3, prod['name'])    
                worksheet.write(1 + conteo, 4, "Code:", column_heading_style) 
                worksheet.write(1 + conteo, 5, prod['default_code'])    
                worksheet.write(2 + conteo, 2, "Current Company:", column_heading_style)
                worksheet.write(2 + conteo, 3, self.company.name)
                worksheet.write(1+ conteo, 6, "Location:", column_heading_style)
                if self.aplica == "ubicacion":                 
                 worksheet.write(1+ conteo, 7, self.ubicacion.complete_name)
                if self.aplica == "todas":  
                 worksheet.write(1+ conteo, 7, "All Ubication")
                #ubi_hijo = todfact.ubicacion.name
                #ubi_pad = todfact.ubicacion.location_id.name
                #worksheet.write(1, 5, str(ubi_pad) + "/" + str(ubi_hijo))
                worksheet.write(4+ conteo, 0, _('Date'), column_heading_style)
                worksheet.write(4+ conteo, 1, _('Date_Cre'), column_heading_style)
                worksheet.write(4+ conteo, 2, _('User_Cre'), column_heading_style)
                worksheet.write(4+ conteo, 3, _('Location'), column_heading_style)                
                worksheet.write(4+ conteo, 4, _('Concept'), column_heading_style)
                worksheet.write(4+ conteo, 5, _('U_In'), column_heading_style)
                worksheet.write(4+ conteo, 6, _('U_Out'), column_heading_style)
                worksheet.write(4+ conteo, 7, _('U_balance'), column_heading_style)
                worksheet.write(4+ conteo, 8, _("Costo_Uni"), column_heading_style)
                worksheet.write(4+ conteo, 9, _('V_In'), column_heading_style)
                worksheet.write(4+ conteo, 10, _('V_Out'), column_heading_style)
                worksheet.write(4+ conteo, 11, _('V_balance'), column_heading_style)        
                worksheet.write(4+ conteo, 12, _('Origin'), column_heading_style)
                worksheet.write(4+ conteo, 13, _('Pickin'), column_heading_style)
                worksheet.write(4+ conteo, 14, _('Invoice'), column_heading_style)
                worksheet.write(4+ conteo, 15, _('Inventory'), column_heading_style)
                worksheet.write(4+ conteo, 16, _('Invoice Supplier'), column_heading_style)
                worksheet.write(4+ conteo, 17, _('Customer/Supplier'), column_heading_style)
                query_total = self._moviento_completo()
                query_saldo_anterior = """
                    select (SUM(u_entrada)-SUM(u_salida))as u_ante , 
                    (SUM(v_entrada)-SUM(v_salida))as v_ante  from (
                """ + query_total + """


                )as saldo_ante where date < %s --) estes espara obteber el saldo anterior

                        """
                
                producto = prod['id']
                ubicacion = 0  
                compan=self.company.id
                 
                if self.aplica == "todas":
                  ubicacion = 0   
                if self.aplica == "ubicacion":
                   ubicacion = self.ubicacion.id   
                date_from = self.date_from
                query_saldo_anterior_param = (producto,ubicacion,compan,producto,ubicacion,compan,producto,compan,date_from)
                self.env.cr.execute(query_saldo_anterior, query_saldo_anterior_param)

                saldo_anterior = self.env.cr.dictfetchall()
                for s_ante in saldo_anterior:
                  worksheet.write(5+ conteo, 1, "Saldo anterior")
                  worksheet.write(5+ conteo, 4, s_ante['u_ante'],number_format)
                  worksheet.write(5+ conteo, 8, s_ante['v_ante'],number_format)
                
                #Repasamos movimiento completo 
                query_total = self._moviento_completo()
                query_movimiento = """
                select * from (
                """ + query_total + """

                ) as mov where date >=%s and date <=%s 

                """

                producto = prod['id']
                ubicacion = 0  
                compan=self.company.id
                 
                if self.aplica == "todas":
                  ubicacion = 0   
                if self.aplica == "ubicacion":
                   ubicacion = self.ubicacion.id                
                
                date_from = self.date_from
                date_to = self.date_to
             
                query_movimiento_param = (producto,ubicacion,compan,producto,ubicacion,compan,producto,compan, date_from, date_to)
                self.env.cr.execute(query_movimiento, query_movimiento_param)

                movim = self.env.cr.dictfetchall()
                tm=0
                ini2=0
                for mov in movim: 
                    tm+=1
                    ini2 = 6
                    
                    ##################################
                    # zh=self.env.user.tz                      
                    # format_hora = "%d-%m-%Y %H:%M:%S %Z%z" 
                    # format_dat="%d-%m-%Y" 
                    # f_Cre = mov['dat_cre']       
                    # fe_creacion= f_Cre.astimezone(timezone(zh))   # esto es un datetime
                    # fecha_cre=fe_creacion.strftime(format_hora) #convertimos a string
                    # #fecha_cre = datetime.strptime(fe_creacion,format_hora)        
                    # #fecha_cre = datetime.strptime(fe_creacion,format_hora) CONVIERTE DE STRING A DATETIME
                    # fechafecha=fe_creacion.strftime(format_dat)
                    ################################
                    worksheet.write(tm + ini2+ conteo, 0, mov['date'],date_format)   
                    worksheet.write(tm + ini2+ conteo, 1, mov['dat_cre'],date_format)
                    ##################################
                    
                    worksheet.write(tm + ini2+ conteo, 2, mov['user_name'])
                    worksheet.write(tm + ini2+ conteo, 3, mov['locat_name'])
                    worksheet.write(tm + ini2+ conteo, 4, mov['reference'])
                    worksheet.write(tm + ini2+ conteo, 5, mov['u_entrada'], number_format)
                    worksheet.write(tm + ini2+ conteo, 6,  mov['u_salida'], number_format)
                    worksheet.write(tm + ini2+ conteo, 7, mov['u_saldo'], number_format)
                    worksheet.write(tm + ini2+ conteo, 8, mov['costo_unit'], number_format)
                    worksheet.write(tm + ini2+ conteo, 9,  mov['v_entrada'], number_format)   
                    worksheet.write(tm + ini2+ conteo, 10, mov['v_salida'], number_format)                   
                    worksheet.write(tm + ini2+ conteo, 11,  mov['v_saldo'], number_format)                  
                    worksheet.write(tm + ini2+ conteo, 12,  mov['origin'], number_format) 
                    if  mov['picking_id'] :
                     picking = self.env['stock.picking'].search([('id', '=', mov['picking_id'])])                  
                     worksheet.write(tm + ini2+ conteo, 13, picking.name )
                    movimiento=mov['origin']
                    factura_num= self._buscar_factura_reportexcel(movimiento)
                    worksheet.write(tm + ini2+ conteo, 14, factura_num)                      
                    worksheet.write(tm + ini2+ conteo, 15, mov['inventory_id'])    

                    if  factura_num:
                      factura_cl_prov= self.env['account.move'].search([('name', '=', factura_num)])                         
                      worksheet.write(tm + ini2+ conteo, 17, factura_cl_prov.partner_id.name) 
                      if  factura_cl_prov.move_type=="in_invoice":
                        worksheet.write(tm + ini2+ conteo, 16, factura_cl_prov.ref)
                    
                      



                worksheet.write(tm + conteo + 7, 1,_('====================>>>>  End product :') +  prod['name'], column_heading_style)

                total=  tm +  conteo + 9

                #borramos el conteo
                query_borrarconteo = """
                delete from kardex_productos_inventario_conteo

                """                
                self.env.cr.execute(query_borrarconteo, )

                #insertamos conteo
                query_totalline = """
                insert into kardex_productos_inventario_conteo ( detalle_conteo) VALUES (%s)

                """
                query_totalline_param=(total,)
                self.env.cr.execute(query_totalline,  query_totalline_param)



                        

        fp = io.BytesIO()
        workbook.save(fp)
        excel_file = base64.encodebytes(fp.getvalue())


        self.excel_binary = excel_file
        nombre_tabla = "Kardex Report.xls"
        self.file_name = nombre_tabla
        fp.close()

    
    
    
    def _action_imprimir_excel(self, ):

        workbook = xlwt.Workbook()
        column_heading_style = easyxf('font:height 200;font:bold True;')
        worksheet = workbook.add_sheet('Kardex report')
        date_format = xlwt.XFStyle()
        date_format.num_format_str = 'dd/mm/yyyy'

        number_format = xlwt.XFStyle()
        number_format.num_format_str = '#,##0.00'

        # Ponemos los primeros encabezados
        worksheet.write(0, 0, _('Kardex report product'), column_heading_style)

        query_rorte = """
        select Max(id) as id  from kardex_productos_mov 
    """
        self.env.cr.execute(query_rorte, )
        tr = self.env.cr.dictfetchall()
        for tr_t in tr:
            todo_reporte = self.env['kardex.productos.mov'].search([('id', '=', int(tr_t['id']))])
            tf = 0
            for todfact in todo_reporte:
                worksheet.write(1, 0, "Date from:", column_heading_style)
                worksheet.write(1, 1, todfact.date_from, date_format)
                worksheet.write(2, 0, "Date to:", column_heading_style)
                worksheet.write(2, 1, todfact.date_to, date_format)

                worksheet.write(1, 2, "Product:", column_heading_style)
                worksheet.write(1, 3, todfact.product.name)
                worksheet.write(2, 2, "Current Company:", column_heading_style)
                worksheet.write(2, 3, todfact.company.name)
                worksheet.write(1, 4, "Code:", column_heading_style)
                worksheet.write(1, 5,todfact.product.default_code)
                worksheet.write(1, 6, "Location:", column_heading_style)
                if self.aplica == "todas" :
                 worksheet.write(1, 7, "ALL")
                if self.aplica == "ubicacion" : 
                 worksheet.write(1, 7, self.ubicacion.complete_name)   

                # Ponemos los primeros encabezados del detalle
        worksheet.write(4, 0, _('Date'), column_heading_style)
        worksheet.write(4, 1, _('Date_Cre'), column_heading_style)
        worksheet.write(4, 2, _('User'), column_heading_style)
        worksheet.write(4, 3, _('Location Name'), column_heading_style)
        worksheet.write(4, 4, _('Concept'), column_heading_style)
        worksheet.write(4, 5, _('U_In'), column_heading_style)
        worksheet.write(4, 6, _('U_Out'), column_heading_style)
        worksheet.write(4, 7, _('U_balance'), column_heading_style)
        worksheet.write(4, 8, _("Costo_Uni"), column_heading_style)
        worksheet.write(4, 9, _('V_In'), column_heading_style)
        worksheet.write(4, 10, _('V_Out'), column_heading_style)
        worksheet.write(4, 11, _('V_balance'), column_heading_style)        
        worksheet.write(4, 12, _('Origin'), column_heading_style)
        worksheet.write(4, 13, _('Pickin'), column_heading_style)
        worksheet.write(4, 14, _('Invoice'), column_heading_style)
        worksheet.write(4, 15, _('Inventory'), column_heading_style)
        worksheet.write(4, 16, _('Invoice Supplier'), column_heading_style)
        worksheet.write(4, 17, _('Customer/Supplier'), column_heading_style)
       


        heading = "Product Kardex Detail"
        # worksheet.write_merge(5, 0, 5,13, heading, easyxf('font:height 200; align: horiz center;pattern: pattern solid, fore_color black; font: color white; font:bold True;' "borders: top thin,bottom thin"))
        # Se tiene que hacer de ultimo para saber cuanto mide todo

        # se recorre el reporte

        todo_reporte = self.env['kardex.productos.mov.detalle'].search(
            [('obj_kardex_mostrarmovi', '=', int(tr_t['id']))])
        tf = 0
        for todfact in todo_reporte:
            tf += 1
            ini = 5
            if   todfact.date  != False :
             worksheet.write(tf + ini, 0, todfact.date, date_format)
             worksheet.write(tf + ini, 1,todfact.date_cre)
             ##################################
             #  zh=self.env.user.tz  
             #  format = "%Y-%m-%d %H:%M:%S %Z%z"             
             #fecha_cre = datetime.strptime(fe_creacion,format_hora) CONVIERTE DE STRING A DATETIME
             #  f_Cre =datetime.datetime.strptime(todfact.date_cre, format) 
             #     #now_utc = datetime.now(timezone('UTC'))             
             #  fe_creacion= f_Cre.astimezone(timezone(zh))              
             #  fecha_cre = fe_creacion.strftime(format)
             #  worksheet.write(tf + ini, 1, fecha_cre, date_format)
             ##################################             
             #name_user = self.env['res.users'].search([('id', '=', todfact.usuario)]) 
            if   todfact.usuario.name  != False :
             worksheet.write(tf + ini, 2, todfact.usuario.name)
            if   todfact.location_name.complete_name  != False : 
             worksheet.write(tf + ini, 3, todfact.location_name.complete_name)
            worksheet.write(tf + ini, 4, todfact.concepto)
            worksheet.write(tf + ini, 5, todfact.u_entrada, number_format)
            worksheet.write(tf + ini, 6, todfact.u_salida, number_format)
            worksheet.write(tf + ini, 7, todfact.u_saldo, number_format)
            worksheet.write(tf + ini, 8, todfact.costo_unit, number_format)
            worksheet.write(tf + ini, 9, todfact.v_entrada, number_format)
            worksheet.write(tf + ini, 10, todfact.v_salida, number_format)
            worksheet.write(tf + ini, 11, todfact.v_saldo, number_format)            
            if   todfact.origin != False :
             worksheet.write(tf + ini, 12, todfact.origin, number_format)
            if   todfact.picking_id.name != False :
             worksheet.write(tf + ini, 13, todfact.picking_id.name)
            if   todfact.account_invoice.name != False : 
             worksheet.write(tf + ini, 14, todfact.account_invoice.name)
            if   todfact.inventario != False :  
              worksheet.write(tf + ini, 15, todfact.inventario)
            if   todfact.fact_supplier != False :   
                worksheet.write(tf + ini, 16, todfact.fact_supplier)
            if   todfact.custumer_supplier != False :   
                worksheet.write(tf + ini, 17, todfact.custumer_supplier)


            # action = self.env.ref('base.action_res_company_form')
            # msg = _('finished report')
            # raise RedirectWarning(msg, action.id, _('OK'))
    #         return {
    #     'type': 'ir.actions.client',
    #     'tag': 'action_warn',
    #     'name': _('Aviso'),
    #     'context' : "",
    #     'params': {
    #        'title': _('Aviso'),
    #        'text': _(u'Mensaje para el usuario'),
    #        'sticky': True
    #    }}
             


        fp = io.BytesIO()
        workbook.save(fp)
        excel_file = base64.encodebytes(fp.getvalue())


        self.excel_binary = excel_file
        nombre_tabla = "Kardex Report.xls"
        self.file_name = nombre_tabla
        fp.close()
       
        
    # @api.depends('company')
    # def _actualizar_compania(self):
    #   self.company=domain=[('company_id', '=', self.company.id)]

    @api.onchange('company')
    def _cambio_company(self):
        #       # Set ubucacion ID
        if self.company:
            return {'domain': {'ubicacion': [('company_id', '=', self.company.id), ('usage', '=', "internal")]}}

            # @api.one

    def _borracampos(self):
        self.cantidad_inicial = ""
        self.cantidad_final = ""
        self.costo_promedio = ""
        self.costo_total = ""
        self.aplica = "todas"
        self.company = ""

    def buscar_producto(self):        
        if self.date_from > self.date_to:
            raise UserError(_("The Start date cannot be less than the end date "))
        else:
            if self.product  and self.select_product=="products": 
               self._borra_datos_tabla()
            if not self.product  and self.select_product=="products": 
             raise UserError(_("Must select one product"))
            if self.grupo_producto  and self.select_product=="todas": 
               self._action_imprimir_grupo_inventario_excel()
               #self._tree_elem()
            if not self.grupo_producto   and self.select_product=="todas": 
               raise UserError(_("Must select one Group"))          
        


    def _borra_datos_tabla(self):
        query_rorte = """
        select Max(id) as id  from kardex_productos_mov 
    """
        self.env.cr.execute(query_rorte, )
        tr = self.env.cr.dictfetchall()
        for tr_t in tr:

            todo = self.env['kardex.productos.mov'].search([('id', '<', int(tr_t['id']))])
            for tod in todo:
                tod.unlink()

            todo_reporte = self.env['kardex.productos.mov.detalle'].search([('id', '<', int(tr_t['id']))])
            for tod in todo_reporte:
                tod.unlink()

        for karde in self:
            karde.obj_kardex.unlink()

        # Empezamos a realizar el saldo
        self._saldo_anterior()

    def _saldo_anterior(self):

        query_total = self._moviento_completo()
        query_saldo_anterior = """
      select (SUM(u_entrada)-SUM(u_salida))as u_ante , 
      (SUM(v_entrada)-SUM(v_salida))as v_ante  from (
""" + query_total + """


)as saldo_ante where date < %s --) estes espara obteber el saldo anterior

        """
        producto = self.product.id
        ubicacion = 0 
        compan=self.company.id

        date_from = self.date_from
       
        if self.aplica == "todas":
            ubicacion = 0   
        if self.aplica == "ubicacion":
          ubicacion = self.ubicacion.id   
        
        
        query_saldo_anterior_param = (producto,ubicacion,compan, producto,ubicacion,compan, producto,compan, date_from)

        self.env.cr.execute(query_saldo_anterior, query_saldo_anterior_param)

        saldo_anterior = self.env.cr.dictfetchall()
        for linea in saldo_anterior:
            self.cantidad_inicial = linea['u_ante']
            self.costo_total_inicial = linea['v_ante']
            if self.costo_total_inicial == 0:
                self.costo_promedio_inicial = 0
            if self.costo_total_inicial > 0:
                self.costo_promedio_inicial = self.costo_total_inicial / self.cantidad_inicial

        # Ponemos el saldo anteririor en la tabla
        self._saldo_anterior_tabla()

    def _saldo_anterior_tabla(self):
        for kardex in self:
            concepto = "Previous balance"
            u_saldo = self.cantidad_inicial
            costo_uni = self.costo_promedio_inicial
            v_saldo = self.costo_total_inicial
            line = ({'concepto': concepto, 'u_saldo': u_saldo, 'costo_unit': costo_uni,
                     'v_saldo': v_saldo,
                     })
            lines = [(0, 0, line)]
            kardex.write({'obj_kardex': lines})
        self._movimiento_producto()

    def _movimiento_producto(self):
       

        
        query_total = self._moviento_completo()
        query_movimiento = """
    select * from (
      """ + query_total + """

    ) as mov where date >=%s and date <=%s 

    """

        
        producto = self.product.id
        ubicacion = 0 
        compan=self.company.id

        date_from = self.date_from
        date_to = self.date_to      
        
                 
        if self.aplica == "todas":
            ubicacion = 0   
        if self.aplica == "ubicacion":
          ubicacion = self.ubicacion.id  
        
        
        query_movimiento_param = (producto,ubicacion,compan, producto,ubicacion,compan, producto,compan, date_from, date_to)
        self.env.cr.execute(query_movimiento, query_movimiento_param)

        movim = self.env.cr.dictfetchall()
        for mov in movim:
            for kardex in self:               
                ##################################
                # zh=self.env.user.tz  
                # #format_hora = "%Y-%m-%d %H:%M:%S %Z%z"  
                # format_hora = "%d-%m-%Y %H:%M:%S %Z%z"                
                # #now_utc = datetime.now(timezone('UTC'))             
                # fe_creacion= f_Cre.astimezone(timezone(zh))   # esto es un datetime
                # fecha_cre=  fe_creacion            
                # #fecha_cre = datetime.strptime(fe_creacion,format_hora) CONVIERTE DE STRING A DATETIME
                # ################################
                # # formato_fecha= "%d-%m-%Y"  
                # # date()
                # # #fecha = mov['date']
                # # fecha_fe=mov['dat_cre']
                # # fecha_fech=fecha_fe.astimezone(timezone(zh))
                # f_Cre = mov['dat_cre']
                fecha=mov['date']   
                fecha_cre=mov['dat_cre']             
                user_id = mov['user_id']  
                location_id = mov['location_id']                
                concepto = mov['reference']
                u_entrada = mov['u_entrada']
                u_salida = mov['u_salida']
                u_saldo = mov['u_saldo']
                costo_unit = mov['costo_unit']
                v_entrada = mov['v_entrada']
                v_salida = mov['v_salida']
                v_saldo = mov['v_saldo']
                origin = mov['origin']
                picking_id = mov['picking_id']
                inventario = mov['inventory_id']
                movimiento=mov['origin']
                factura_num= self._buscar_factura_reportexcel(movimiento)
                
                if factura_num:                 
                  fact_num = self.env['account.move'].search([('name', '=', factura_num)])  
                  if fact_num.partner_id.name:                   
                   cust_sup= fact_num.partner_id.name 
                  else :
                   cust_sup= ""   

                  if fact_num.ref:                   
                   ref = fact_num.ref
                  else :
                   ref =""
                
                else :
                  ref =""
                  cust_sup= ""

                line = ({'date': fecha,'date_cre': fecha_cre,'usuario': user_id,'location_name': location_id, 'concepto': concepto, 'u_entrada': u_entrada,
                         'u_salida': u_salida, 'u_saldo': u_saldo, 'costo_unit': costo_unit,
                         'v_entrada': v_entrada, 'v_salida': v_salida, 'v_saldo': v_saldo,
                         'origin': origin, 'picking_id': picking_id, 'inventario': inventario,
                         'fact_supplier': ref,'custumer_supplier': cust_sup,

                         })
                lines = [(0, 0, line)]
                kardex.write({'obj_kardex': lines})
        self._saldo_final()

    def _saldo_final(self):

        query_total = self._moviento_completo()
        query_saldo_final = """
      select (SUM(u_entrada)-SUM(u_salida))as u_saldo , 
      (SUM(v_entrada)-SUM(v_salida))as v_saldo  from (
    """ + query_total + """

     )as saldo_ante where date <= %s --) estes espara obteber el saldo final

        """
        producto = self.product.id
        ubicacion = 0 
        compan=self.company.id
        date_to = self.date_to
        
        if self.aplica == "todas":
            ubicacion = 0   
        if self.aplica == "ubicacion":
          ubicacion = self.ubicacion.id        
        
        
        query_saldo_final_param = (producto,ubicacion,compan, producto,ubicacion,compan, producto,compan, date_to)

        self.env.cr.execute(query_saldo_final, query_saldo_final_param)

        saldo_final = self.env.cr.dictfetchall()
        for linea in saldo_final:

            self.cantidad_final = linea['u_saldo']
            self.costo_total = linea['v_saldo']
            if self.cantidad_final> 0:
                self.costo_promedio = self.costo_total / self.cantidad_final

        # buscamos las facturas
        self._buscar_factura()

    def _moviento_completo(self):
        zh=self.env.user.tz
        product="and sm.product_id=%s"      

        local_des = ""
        location_id = ""
        
        compan="and  sm.company_id=%s "
        
        if self.aplica == "todas":
            local_des = "and sm.location_dest_id >%s"
            location_id = "and sm.location_id > %s"        
            
        if self.aplica == "ubicacion":
            local_des = " and sm.location_dest_id=%s"
            location_id = "and sm.location_id=%s"
          


        query_movimiento = """



-------1)COMIENZA EL PRIMER SELECT      
 select name_product,default_code,user_id, user_name,location_id,locat_name,id,
 CAST(date AS date),date as dat_cre,company_id, product,nombre,u_entrada, u_salida,
 u_saldo,costo_unit,v_entrada,v_salida,v_saldo,state,origin,reference,usage,complete_name,
 ubicacion,inventory_id ,picking_id  
 from 
 (

---------- 2) EMPIEZA EL SEGUNDO SELECT
	 select name_product,default_code, user_id, user_name,location_id,locat_name,id,
     date_expected as date,company_id ,product_id as product,name as nombre,u_entrada,
     u_salida,SUM(u_entrada-u_salida)over (order by date_expected asc,id_todo asc)as u_saldo,
     costo_unit,v_entrada,v_salida,SUM(v_entrada-v_salida)over (order by date_expected asc,
     id_todo asc)as  v_saldo,state,origin,reference,usage,complete_name,ubicacion,inventory_id ,
     picking_id  
	  from 
      (

------------------- 3)COMIENZA EL TERCER SELECT
            select  Row_Number() over (order by id) as id_todo,name_product,default_code,
            user_id, user_name,location_id,locat_name,id,date_expected,product_id,name,
            company_id, u_entrada,u_salida,costo_unit, v_entrada,v_salida,v_saldo,state,
            origin,reference,usage,complete_name,ubicacion,write_uid,inventory_id,picking_id  		  
			from 
			(   

-----------3A)SELECT INTERMEDIO

            select  name_product,default_code,
            user_id, user_name,location_id,locat_name,id,date_expected,product_id,name,
            company_id, u_entrada,u_salida,costo_unit, v_entrada,v_salida,v_saldo,state,
            origin,reference,usage,complete_name,ubicacion,write_uid,inventory_id,picking_id  		  
			from 
			(   
           
---------------------------------------- 4) EMPIEZA LA UNION
                            select name_product,default_code,user_id, user_name,location_id,
                            locat_name,id,date_expected,product_id,name,company_id, u_entrada,
                            u_salida,  
                            costo_unit
                            , v_entrada,v_salida,v_saldo,state,origin,reference,
                            usage,complete_name,ubicacion,write_uid,inventory_id,picking_id   
                            from 
                            (
                                select  sld.usage as bg_out,pt.name as name_product,pp.default_code,ru.id as user_id,
                                rp.name as user_name,sl.id as location_id,
                                sl.complete_name as locat_name,sm.id,
                                sm.write_date   AT TIME ZONE 'UTC'  AT TIME ZONE '"""+zh+"""' as date_expected,sm.product_id,
                                sm.name,sm.company_id,sm.product_qty as u_entrada,(sm.product_qty * 0)u_salida,
                                (sm.price_unit ) as costo_unit
                                ,(sm.price_unit * sm.product_qty) as v_entrada,(sm.product_qty  * 0)v_salida,
                                (sm.product_qty  *0)v_saldo,sm.state,sm.origin,sm.reference,
                                sl.usage,sl.complete_name,(sm.location_dest_id)as ubicacion,sm.write_uid,
                                sm.is_inventory as inventory_id ,sm.picking_id
                                from stock_move sm  inner join stock_location sl on sm.location_dest_id=sl.id 
                                inner join stock_location sld on sm.location_id=sld.id 
                                LEFT join account_move am on am.stock_move_id= sm.id
                                LEFT join stock_picking sp on sm.picking_id=sp.id
                                LEFT join res_users ru on sm.write_uid=ru.id
                                LEFT join res_partner rp on rp.id=ru.partner_id
                                LEFT join product_product pp on pp.id= sm.product_id
                                LEFT join product_template pt on pt.id= pp.product_tmpl_id
                                where   
                                  sl.usage ='internal' and sld.usage !='view'
                                    """ + product + """  and sm.state='done'  """ + local_des + """ 
                                    """ + compan + """ 

                                    order by date_expected asc 
                            )as    sl   

                            ----------- 2) termina unimos entradas

                            UNION

                            ------------- 1) unimos salidas
                            select name_product,default_code,user_id,user_name,location_id,locat_name,id,date_expected
                             ,product_id,name,company_id, u_entrada,u_salida,costo_unit
                            ,v_entrada,v_salida,v_saldo,state,origin,reference,
                            usage,complete_name,ubicacion,write_uid,inventory_id,picking_id  
                            from
                            (
                                
                                    select  sld.usage as bg_in,pt.name as name_product,pp.default_code,ru.id as user_id,
                                    rp.name as user_name,
                                    sl.id as location_id,sl.complete_name as locat_name,sm.id,
                                    sm.write_date  AT TIME ZONE 'UTC'  AT TIME ZONE '"""+zh+"""'  as date_expected,
                                    sm.product_id,sm.name,sm.company_id,(sm.product_qty * 0) as u_entrada,
                                    sm.product_qty as u_salida,(am.amount_total/sm.product_qty) as costo_unit
                                    ,(0)as v_entrada,(am.amount_total)v_salida,
                                    (sm.product_qty  *0)v_saldo,
                                     sm.state,sm.origin,sm.reference ,sl.usage,sl.complete_name,
                                     (sm.location_id)as ubicacion,sm.write_uid,sm.is_inventory as inventory_id ,
                                     sm.picking_id 
                                    from stock_move sm  inner join stock_location sl on sm.location_id=sl.id 
                                    inner join stock_location sld on sm.location_dest_id=sld.id 
                                    LEFT join account_move am on am.stock_move_id= sm.id
                                    LEFT join stock_picking sp on sm.picking_id=sp.id
                                    LEFT join res_users ru on sm.write_uid=ru.id
                                    LEFT join res_partner rp on rp.id=ru.partner_id
                                    LEFT join product_product pp on pp.id= sm.product_id
                                    LEFT join product_template pt on pt.id= pp.product_tmpl_id

                                    where  sl.usage ='internal'and sld.usage !='view'
                                            """ + product + """ and sm.state='done'  """ + location_id + """
                                                """ + compan + """ 
                                            order by date_expected asc
                                            

                             ) as sl1
                             
                             UNION
                             ---------------1)Unimos ajustes de costo
                             
                            
                            select name_product,default_code,user_id,user_name,location_id,locat_name,id,
                            date_expected ,product_id,name,company_id, u_entrada,u_salida,costo_unit
                            ,v_entrada,v_salida,v_saldo,state,origin,reference,
                            usage,complete_name,ubicacion,write_uid,inventory_id,picking_id  
                            from
                            (
                               select * from (
                                    select pt.name as name_product,pp.default_code,ru.id as user_id,rp.name as user_name,
                                    sl.id as location_id,sl.complete_name as locat_name,svl.id,
                                    svl.write_date  AT TIME ZONE 'UTC' AT TIME ZONE '"""+zh+"""' as date_expected,
                                    svl.product_id,svl.description as name,svl.company_id,(svl.value * 0) as u_entrada,
                                    (svl.value * 0) as u_salida,(svl.value * 0 ) as costo_unit
                                    ,(svl.value)as v_entrada,(svl.value * 0)v_salida,
                                    (svl.value * 0)v_saldo,CAST (svl.quantity AS varchar) as state,CAST (svl.description  AS varchar) as origin,svl.description as reference,CAST (svl.quantity AS varchar)as usage,sl.complete_name
                                    ,(sm.location_id)as ubicacion,sm.write_uid,sm.is_inventory as inventory_id ,sm.picking_id 
                                            from stock_valuation_layer svl   
                                            LEFT join stock_landed_cost slc on slc.id = svl.stock_landed_cost_id
                                            LEFT  join  stock_move sm  on  svl.stock_move_id = sm.id   
                                            LEFT  join stock_location sl on sm.location_id=sl.id   
                                            LEFT join account_move am on am.id= svl.account_move_id
                                            LEFT join stock_picking sp on sm.picking_id=sp.id
                                            LEFT join res_users ru on svl.write_uid=ru.id
                                            LEFT join res_partner rp on rp.id=ru.partner_id
                                            LEFT join product_product pp on pp.id= svl.product_id
                                            LEFT join product_template pt on pt.id= pp.product_tmpl_id

                                        where

                                        svl.unit_cost is null   or stock_landed_cost_id>0

                                       ) as valor where   

                                                                                               
                                        product_id=%s  and
                                        company_id=%s                              
                                   

                                

                             )as sl2
                                        
-------------------------------------------4) termina la union	----------------------------	
             ) as kardex order by date_expected asc ------------3A)termina el tercer select INTERMEDIO
         ) as kardex  ------------------------------3)termina el tercer select
	) as kardex  ------------------------ 2) TERMINA EL SEGUNDO SELECT
)as kardex2    ----------------1)TERMINA EL PRIMER SELECT  



        """
        return query_movimiento

    def _buscar_factura(self):
        for fact in self.obj_kardex:
            if fact.origin:
                query_origen = """
        select Min(id) as id from account_move where invoice_origin = %s 
        """
                query_origen_param = (fact.origin,)

                self.env.cr.execute(query_origen, query_origen_param)

                movim = self.env.cr.dictfetchall()
                for mov in movim:
                    # #  facturas=self.env['account.invoice'].search([('origin','=',fact.origin)])

                    fact.account_invoice = mov['id']

        self._action_imprimir_excel()

    def _buscar_factura_reportexcel(self,origen):
       
        query_origen = """
        select Min(id) as id,name from account_move where invoice_origin  = %s 
         group by name 
        """
        query_origen_param = (origen,)
        self.env.cr.execute(query_origen, query_origen_param)
        movim = self.env.cr.dictfetchall()
        nombre=""
        for mov in movim:
          nombre=  mov['name']

        return nombre
     
    


class kardex_productos_inventario_detalle(models.TransientModel):
    _name = 'kardex.productos.mov.detalle'
    _description = "kardex productos"

    obj_kardex_mostrarmovi = fields.Many2one('kardex.productos.mov')

    # @api.model
    # def _ver_compos_costos(self): 
    #     if  self.env.user.ver_costo == True :  
    #       poner="administrador"
    #     if  self.env.user.ver_costo == False :    
    #       poner="dependiente"  
    #     return  poner


    # ver_campos_costo= fields.Char(string='Ver costo',default=_ver_compos_costos)
    date = fields.Date(string='Date')
    date_cre=fields.Char(string='Date_cre')
    usuario= fields.Many2one('res.users')
    location_name=fields.Many2one('stock.location')
    concepto = fields.Char(string='Description')
    company_id = fields.Many2one('res.company', string='Company')
    u_entrada = fields.Float()
    u_salida = fields.Float()
    u_saldo = fields.Float()
    costo_unit = fields.Float()
    v_entrada = fields.Float()
    v_salida = fields.Float()
    v_saldo = fields.Float()
    costo_prom = fields.Float()
    state = fields.Char(string='Estado')
    origin = fields.Char(string='Origien')
    picking_id = fields.Many2one('stock.picking', string='Picking')
    account_invoice = fields.Many2one('account.move', string='Factura')
    inventario = fields.Char(string='inventory')    
    fact_supplier = fields.Char(string='Inv.supp')
    custumer_supplier = fields.Char(string='Name')

class kardex_productos_inventario_conteo(models.TransientModel):
    _name = 'kardex.productos.inventario.conteo'
    _description = "Kardex  report conteo"

    detalle_conteo = fields.Integer(string='d_conbteo')
    #debe = fields.Float(string='Debit')   

