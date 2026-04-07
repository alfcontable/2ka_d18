# -*- coding: utf-8 -*-

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



from odoo.tools.misc import xlwt
import io
import base64
from xlwt import easyxf

 


class kardex_productos_inventario2(models.TransientModel):
    _name = 'kardex.productos.mov2'
    _description = "kardex productos"

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
        fecha_actual= pytz.UTC.localize(datetime.now()).astimezone(timezone(self.env.user.tz))
        return  fecha_actual

    @api.model
    def _poner_revos(self):       
        fecha_actual= pytz.timezone('America/Managua')
        return  fecha_actual
   
        #self.encabezado_reporte=self.env.user.company_id.encabezado.reporte

    @api.model
    def _poner_nombre_empresa(self):
       company_id = self.env.company.name       
       nombre_empresa=company_id
       return nombre_empresa

    @api.model
    def _poner_registro(self):
       #registro_fiscal=self.env.user.company_id.vat
       registro_fiscal=self.env.company.vat
       return registro_fiscal

    @api.model
    def _poner_encabezado_reporte(self):
       # encabezado_reporte=self.env.user.company_id.encabezado_reporte
       encabezado_reporte=self.env.company.encabezado_reporte
       return encabezado_reporte

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
    company = fields.Many2one('res.company', required=True,readonly=True, default=lambda self: self.env.company.id,
                              string='Current Company')

    ubicacion = fields.Many2one('stock.location', domain=[('usage', '=', "internal")], string='Location')

    date_from = fields.Date(string='Date from',default=_poner_fecha)
    date_to = fields.Date(string='Date to', default=_poner_fecha)
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
                                  default=lambda self: self.env.company.currency_id, readonly=True)

    
    encabezado_reporte = fields.Text(string='Encabezado reporte',default=_poner_encabezado_reporte)
    nombre_empresa=fields.Char(string='Empresa',default=_poner_nombre_empresa)
    registro_fiscal=fields.Char(string='Registro fiscal',default=_poner_registro)

    obj_kardex = fields.One2many(comodel_name='kardex.productos.mov.detalle2', inverse_name='obj_kardex_mostrarmovi')

    
    def _action_imprimir_grupo_inventario_excel(self, ):

        
        self.cantidad_final=0
        self.costo_promedio_inicial=0
        self.costo_total_inicial=0
        self.cantidad_final=0
        self.costo_promedio=0
        self.costo_total=0

        workbook = xlwt.Workbook()
        column_heading = easyxf('font:height 200;font:bold True;')
        column_heading_style = easyxf('font:height 200;font:bold True;')
        # column_heading_style = easyxf('font:height 200;font:bold True;pattern: pattern solid, fore_colour grey25')
       
        worksheet = workbook.add_sheet('Kardex report')
        date_format = xlwt.XFStyle()
        date_format.num_format_str = 'dd/mm/yyyy'

        number_format = xlwt.XFStyle()
        number_format.num_format_str = '#,##0.00'

        # Ponemos los primeros encabezados
        # worksheet.write(0, 0, _('KÁRDEX DE EXISTENCIAS - RÉGIMEN GENERAL * NUEVOS SOLES *'), column_heading)
        worksheet.write(0, 0, self.nombre_empresa, column_heading)
        worksheet.write(1, 0, self.encabezado_reporte, column_heading)

        cant_prod=0
        for  grupos  in self.grupo_producto :
        #Vamos agrupando por grupo de productos     
            query_grupos = """
        ---------agrupar productos
select pp.default_code,pp.id,pt.name ->> 'en_US'as name,pt.categ_id,pt.id as id_temp  from product_product  pp
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
                    select * from kardex_productos_inventario_conteo2 order by id  asc
                        """
                
                    self.env.cr.execute(query_lineconteo,)
                    conteo_fila = self.env.cr.dictfetchall()
                    for cont in conteo_fila:
                       conteo = cont['detalle_conteo']

                #Repasamos producto por producto    
                worksheet.write(2 + conteo, 0, "FECHA INICIAL:", column_heading_style)
                worksheet.write(2 + conteo, 1, self.date_from, date_format)
                worksheet.write(3 + conteo, 0, "FECHA FINAL:", column_heading_style)
                worksheet.write(3 + conteo, 1, self.date_to, date_format)
                worksheet.write(2 + conteo, 2, "PRODUCTO:", column_heading_style)               
                worksheet.write(2 + conteo, 3, prod['name'])    
                worksheet.write(2 + conteo, 4, "CODIGO:", column_heading_style) 
                worksheet.write(2 + conteo, 5, prod['default_code'])   
                worksheet.write(3 + conteo, 4, "U/M:", column_heading_style) 
                # pr_pr=self.env['product.product'].search([('id', '=', prod['id'])]) 
                unidad_med=self.env['product.template'].search([('id', '=', prod['id_temp'])])                     
                worksheet.write(3 + conteo, 5, unidad_med.uom_id.name, column_heading_style)  
                worksheet.write(3 + conteo, 2, "COMPAÑIA ACTUAL:", column_heading_style)
                worksheet.write(3 + conteo, 3, self.company.name)
                worksheet.write(2+ conteo, 6, "LOCATION:", column_heading_style)
                if self.aplica == "ubicacion":                 
                 worksheet.write(2+ conteo, 7, self.ubicacion.complete_name)
                if self.aplica == "todas":  
                 worksheet.write(2+ conteo, 7, "All Ubication")
                #ubi_hijo = todfact.ubicacion.name
                #ubi_pad = todfact.ubicacion.location_id.name
                #worksheet.write(1, 5, str(ubi_pad) + "/" + str(ubi_hijo))
                worksheet.write(4+ conteo, 0, _('FECHA'), column_heading_style)
                worksheet.write(4+ conteo, 1, _('FECHA CREACION'), column_heading_style)
                worksheet.write(4+ conteo, 2, _('USUARIO'), column_heading_style)
                worksheet.write(4+ conteo, 3, _('BODEGA'), column_heading_style)                
                worksheet.write(4+ conteo, 4, _('CONCEPTO'), column_heading_style)
                worksheet.write(4+ conteo, 5, _('ENTRADAS'), column_heading_style)
                worksheet.write(4+ conteo, 6, _('SALIDAS'), column_heading_style)
                worksheet.write(4+ conteo, 7, _('SALDO'), column_heading_style)
                # worksheet.write(4+ conteo, 8, _("Costo_Uni"), column_heading_style)
                # worksheet.write(4+ conteo, 9, _('V_In'), column_heading_style)
                # worksheet.write(4+ conteo, 10, _('V_Out'), column_heading_style)
                # worksheet.write(4+ conteo, 11, _('V_balance'), column_heading_style)        
                worksheet.write(4+ conteo, 8, _('DOCUMENTO ORIGEN'), column_heading_style)
                worksheet.write(4+ conteo, 9, _('PICKING'), column_heading_style)
                worksheet.write(4+ conteo, 10, _('FACTURA'), column_heading_style)
                worksheet.write(4+ conteo, 11, _('DOCUMENTO INVENTARIO'), column_heading_style)
                worksheet.write(4+ conteo, 12, _('PROVEEDOR'), column_heading_style)
                worksheet.write(4+ conteo, 13, _('CLIENTE/PROVEEDOR'), column_heading_style)
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
                sum_in=0
                sum_out=0
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
                    # worksheet.write(tm + ini2+ conteo, 8, mov['costo_unit'], number_format)
                    # worksheet.write(tm + ini2+ conteo, 9,  mov['v_entrada'], number_format)   
                    # worksheet.write(tm + ini2+ conteo, 10, mov['v_salida'], number_format)                   
                    # worksheet.write(tm + ini2+ conteo, 11,  mov['v_saldo'], number_format)                  
                    worksheet.write(tm + ini2+ conteo, 8,  mov['origin'], number_format)  
                    picking = self.env['stock.picking'].search([('id', '=', mov['picking_id'])])                  
                    worksheet.write(tm + ini2+ conteo, 9, picking.name )
                    movimiento=mov['origin']
                    factura_name= self._buscar_factura_reportexcel(movimiento)
                    worksheet.write(tm + ini2+ conteo, 10, factura_name)
                    inventory_desc =  mov['inventory_id']
                    worksheet.write(tm + ini2+ conteo, 11, inventory_desc)

                    
                    if  factura_name:
                      factura_cl_prov= self.env['account.move'].search([('name', '=', factura_name)])                         
                      worksheet.write(tm + ini2+ conteo, 13, factura_cl_prov.partner_id.name) 
                      if  factura_cl_prov.move_type=="in_invoice":
                        worksheet.write(tm + ini2+ conteo, 12, factura_cl_prov.ref)

                    if  picking and not factura_name:
                        picking = self.env['stock.picking'].search([('id', '=', mov['picking_id'])]) 
                        worksheet.write(tm + ini2+ conteo, 13, picking.partner_id.display_name) 
                    

                    sum_in=sum_in + mov['u_entrada']
                    sum_out=sum_out +  mov['u_salida']
                worksheet.write(tm + conteo +7, 4,_('TOTAL PRODUCTO'), column_heading_style)    
                worksheet.write(tm + conteo +7, 5,sum_in, number_format)
                worksheet.write(tm + conteo +7, 6, sum_out,number_format)
                worksheet.write(tm + conteo + 8, 1,_('====================>>>>  END PRODUCT:') +  prod['name'], column_heading_style)


                total=  tm +  conteo + 9

                #borramos el conteo
                query_borrarconteo = """
                delete from kardex_productos_inventario_conteo2

                """                
                self.env.cr.execute(query_borrarconteo, )

                #insertamos conteo
                query_totalline = """
                insert into kardex_productos_inventario_conteo2 ( detalle_conteo) VALUES (%s)

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
        #worksheet.write(0, 0, _('KÁRDEX DE EXISTENCIAS - RÉGIMEN GENERAL * NUEVOS SOLES *'), column_heading_style)
       
        worksheet.write(0, 0, self.nombre_empresa, column_heading_style)
        worksheet.write(1, 0, self.encabezado_reporte, column_heading_style)


        query_rorte = """
        select Max(id) as id  from kardex_productos_mov2 
    """
        self.env.cr.execute(query_rorte, )
        tr = self.env.cr.dictfetchall()
        for tr_t in tr:
            todo_reporte = self.env['kardex.productos.mov2'].search([('id', '=', int(tr_t['id']))])
            tf = 0
            for todfact in todo_reporte:
                worksheet.write(2, 0, "FECHA INICIAL:", column_heading_style)
                worksheet.write(2, 1, todfact.date_from, date_format)
                worksheet.write(3, 0, "FECHA FINAL:", column_heading_style)
                worksheet.write(3, 1, todfact.date_to, date_format)

                worksheet.write(2, 2, "PRODUCTO:", column_heading_style)
                worksheet.write(2, 3, todfact.product.name)
                worksheet.write(3, 2, "COMPAÑIA ACTUAL:", column_heading_style)
                worksheet.write(3, 3, todfact.company.name)
                worksheet.write(2, 4, "CODIGO:", column_heading_style)
                worksheet.write(2, 5,todfact.product.default_code)
                worksheet.write(2, 6, "BODEGA:", column_heading_style)
                if self.aplica == "todas" :
                 worksheet.write(2, 7, "ALL")
                if self.aplica == "ubicacion" : 
                 worksheet.write(2, 7, self.ubicacion.complete_name)   

                # Ponemos los primeros encabezados del detalle
        worksheet.write(4, 0, _('FECHA'), column_heading_style)
        worksheet.write(4, 1, _('FECHA_CREACION'), column_heading_style)
        worksheet.write(4, 2, _('USUARIO'), column_heading_style)
        worksheet.write(4, 3, _('BODEGA'), column_heading_style)
        worksheet.write(4, 4, _('CONCEPTO'), column_heading_style)
        worksheet.write(4, 5, _('INGRESO'), column_heading_style)
        worksheet.write(4, 6, _('SALIDA'), column_heading_style)
        worksheet.write(4, 7, _('SALDO'), column_heading_style)
        # worksheet.write(4, 8, _("Costo_Uni"), column_heading_style)
        # worksheet.write(4, 9, _('V_In'), column_heading_style)
        # worksheet.write(4, 10, _('V_Out'), column_heading_style)
        # worksheet.write(4, 11, _('V_balance'), column_heading_style)        
        worksheet.write(4, 8, _('DOCUMENTO ORIGEN'), column_heading_style)
        worksheet.write(4, 9, _('PICKING'), column_heading_style)
        worksheet.write(4, 10, _('FACTURA_SISTEMA'), column_heading_style)
        worksheet.write(4, 11, _('DOC.INVENTARIO'), column_heading_style)
        worksheet.write(4, 12, _('FACTURA PROVEEDOR'), column_heading_style)
        worksheet.write(4, 13, _('CLIENTE/PROVEEDOR'), column_heading_style)

        heading = "Product Kardex Detail"
        # worksheet.write_merge(5, 0, 5,13, heading, easyxf('font:height 200; align: horiz center;pattern: pattern solid, fore_color black; font: color white; font:bold True;' "borders: top thin,bottom thin"))
        # Se tiene que hacer de ultimo para saber cuanto mide todo

        # se recorre el reporte

        todo_reporte = self.env['kardex.productos.mov.detalle2'].search(
            [('obj_kardex_mostrarmovi', '=', int(tr_t['id']))])
        tf = 0
        sum_in=0
        sum_out=0
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
            # worksheet.write(tf + ini, 8, todfact.costo_unit, number_format)
            # worksheet.write(tf + ini, 9, todfact.v_entrada, number_format)
            # worksheet.write(tf + ini, 10, todfact.v_salida, number_format)
            # worksheet.write(tf + ini, 11, todfact.v_saldo, number_format)            
            if   todfact.origin != False :
             worksheet.write(tf + ini, 8, todfact.origin, number_format)
            if   todfact.picking_id.name != False :
             worksheet.write(tf + ini, 9, todfact.picking_id.name)
            if   todfact.account_invoice.name != False : 
             worksheet.write(tf + ini, 10, todfact.account_invoice.name)
            if   todfact.inventario != False :  
             worksheet.write(tf + ini, 11, todfact.inventario)           
            if   todfact.fact_supplier != False :   
                worksheet.write(tf + ini, 12, todfact.fact_supplier)
            if   todfact.custumer_supplier != False :   
                worksheet.write(tf + ini, 13, todfact.custumer_supplier)
            
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
            sum_in=sum_in+todfact.u_entrada
            sum_out=sum_out+todfact.u_salida
        worksheet.write(tf + 6, 4, _('TOTAL PRODUCTO'))
        worksheet.write(tf + 6, 5, sum_in,number_format)
        worksheet.write(tf + 6, 6, sum_out,number_format)



        fp = io.BytesIO()
        workbook.save(fp)
        excel_file = base64.encodebytes(fp.getvalue())

        self.excel_binary = excel_file
        nombre_tabla = "Kardex Report.xls"
        self.file_name = nombre_tabla
        fp.close()
        return {
            'name': 'Pdf.generation.form',
            'type': 'ir.actions.act_window',
            'view_mode': 'form',
            'res_model': 'hr.wizard',
             'view_mode': 'form',
            'view_type': 'form',
            'target': 'new',
            
        }

        
        
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

    def buscar_producto_2(self):
        if self.date_from > self.date_to:
            raise UserError(_("The Start date cannot be less than the end date "))
        else:
            if self.product  and self.select_product=="products": 
               self._borra_datos_tabla()
            if not self.product  and self.select_product=="products": 
             raise UserError(_("Must select one product"))
            if self.grupo_producto  and self.select_product=="todas": 
               self._action_imprimir_grupo_inventario_excel()
            if not self.grupo_producto   and self.select_product=="todas": 
               raise UserError(_("Must select one Group"))          
             
           

    def _borra_datos_tabla(self):
        query_rorte = """
        select Max(id) as id  from kardex_productos_mov2 
    """
        self.env.cr.execute(query_rorte, )
        tr = self.env.cr.dictfetchall()
        for tr_t in tr:

            todo = self.env['kardex.productos.mov2'].search([('id', '<', int(tr_t['id']))])
            for tod in todo:
                tod.unlink()

            todo_reporte = self.env['kardex.productos.mov.detalle2'].search([('id', '<', int(tr_t['id']))])
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
            concepto = "SALDO ANTERIOR"
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
                ref=""
                cust_sup=""
                if factura_num:                 
                  fact_num = self.env['account.move'].search([('name', '=', factura_num)])  
                  fact_num.partner_id.name 
                  cust_sup= fact_num.partner_id.name 
                  ref = fact_num.ref

                if  picking_id and not  factura_num:
                   pick=  self.env['stock.picking'].search([('id', '=', picking_id)])  
                   cust_sup=pick.partner_id.display_name  


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
     id_todo asc)as  v_saldo,state,origin,reference,usage,complete_name,ubicacion,inventory_id ,picking_id  
	  from 
      (

------------------- 3)COMIENZA EL TERCER SELECT
            select  Row_Number() over (order by id) as id_todo,name_product,default_code,
            user_id, user_name,location_id,locat_name,id,date_expected,product_id,name,
            company_id, u_entrada,u_salida,costo_unit, v_entrada,v_salida,v_saldo,state,
            origin,reference,usage,complete_name,ubicacion,create_uid,inventory_id,picking_id  		  
			from 
			(   

-----------3A)SELECT INTERMEDIO

            select  name_product,default_code,
            user_id, user_name,location_id,locat_name,id,date_expected,product_id,name,
            company_id, u_entrada,u_salida,costo_unit, v_entrada,v_salida,v_saldo,state,
            origin,reference,usage,complete_name,ubicacion,create_uid,inventory_id,picking_id  		  
			from 
			(   
           
---------------------------------------- 4) EMPIEZA LA UNION
                            select name_product,default_code,user_id, user_name,location_id,locat_name,id,date_expected,product_id,name,company_id, u_entrada,u_salida,  
                            costo_unit
                            , v_entrada,v_salida,v_saldo,state,origin,reference,
                            usage,complete_name,ubicacion,create_uid,inventory_id,picking_id   
                            from 
                            (
                                select  pt.name as name_product,pp.default_code,ru.id as user_id,rp.name as user_name,sl.id as location_id,sl.complete_name as locat_name,sm.id,sm.write_date AT TIME ZONE 'UTC'  AT TIME ZONE '"""+zh+"""'   as date_expected,sm.product_id,sm.name,sm.company_id,sm.product_qty as u_entrada,(sm.product_qty * 0)u_salida,
                                (am.amount_total_signed/sm.product_qty ) as costo_unit
                                ,(am.amount_total_signed) as v_entrada,(sm.product_qty  * 0)v_salida,(sm.product_qty  *0)v_saldo,sm.state,sm.origin,sm.reference,
                                sl.usage,sl.complete_name,(sm.location_dest_id)as ubicacion,sm.write_uid as create_uid ,sm.is_inventory as inventory_id,sm.picking_id
                                from stock_move sm  inner join stock_location sl on sm.location_dest_id=sl.id 
                                LEFT join account_move am on am.stock_move_id= sm.id
                                LEFT join stock_picking sp on sm.picking_id=sp.id
                                LEFT join res_users ru on sm.write_uid=ru.id
                                LEFT join res_partner rp on rp.id=ru.partner_id
                                LEFT join product_product pp on pp.id= sm.product_id
                                LEFT join product_template pt on pt.id= pp.product_tmpl_id
                                where sl.usage='internal'
                                    """ + product + """  and sm.state='done'  """ + local_des + """ 
                                    """ + compan + """ 

                            )as    sl   

                            ----------- 2) termina unimos entradas

                            UNION

                            ------------- 1) unimos salidas
                            select name_product,default_code,user_id,user_name,location_id,locat_name,id,date_expected
                             ,product_id,name,company_id, u_entrada,u_salida,costo_unit
                            ,v_entrada,v_salida,v_saldo,state,origin,reference,
                            usage,complete_name,ubicacion,create_uid,inventory_id,picking_id  
                            from
                            (
                                
                                   
                                    select pt.name as name_product,pp.default_code,ru.id as user_id,rp.name as user_name,sl.id as location_id,sl.complete_name as locat_name,sm.id,sm.write_date AT TIME ZONE 'UTC'  AT TIME ZONE '"""+zh+"""'   as date_expected,sm.product_id,sm.name,sm.company_id,(sm.product_qty * 0) as u_entrada,
                                    sm.product_qty as u_salida,(am.amount_total_signed/sm.product_qty ) as costo_unit
                                    ,(sm.product_qty *0)as v_entrada,(am.amount_total_signed )v_salida,(sm.product_qty  *0)v_saldo,
                                     sm.state,sm.origin,sm.reference ,sl.usage,sl.complete_name,(sm.location_id)as ubicacion,sm.write_uid as create_uid,sm.is_inventory as inventory_id,sm.picking_id 
                                    from stock_move sm  inner join stock_location sl on sm.location_id=sl.id 
                                    LEFT join account_move am on am.stock_move_id= sm.id
                                    LEFT join stock_picking sp on sm.picking_id=sp.id
                                    LEFT join res_users ru on sm.write_uid=ru.id
                                    LEFT join res_partner rp on rp.id=ru.partner_id
                                    LEFT join product_product pp on pp.id= sm.product_id
                                    LEFT join product_template pt on pt.id= pp.product_tmpl_id

                                    where sl.usage='internal'
                                            """ + product + """ and sm.state='done'  """ + location_id + """
                                                """ + compan + """ 
                                            order by date_expected asc
                                            
                                            

                             ) as sl1
                             
                             UNION
                             ---------------1)Unimos ajustes de costo
                             
                            
                            select name_product,default_code,user_id,user_name,location_id,locat_name,id,
                            date_expected ,product_id,name,company_id, u_entrada,u_salida,costo_unit
                            ,v_entrada,v_salida,v_saldo,state,origin,reference,
                            usage,complete_name,ubicacion,create_uid,inventory_id,picking_id  
                            from
                            (
                               select * from (
                                    select pt.name as name_product,pp.default_code,ru.id as user_id,rp.name as user_name,
                                    sl.id as location_id,sl.complete_name as locat_name,svl.id,
                                    svl.write_date AT TIME ZONE 'UTC'  AT TIME ZONE '"""+zh+"""'  as date_expected,
                                    svl.product_id,svl.description as name,svl.company_id,(svl.value * 0) as u_entrada,
                                    (svl.value * 0) as u_salida,(svl.value * 0 ) as costo_unit
                                    ,(svl.value)as v_entrada,(svl.value * 0)v_salida,
                                    (svl.value * 0)v_saldo,CAST (svl.quantity AS varchar) as state,CAST (svl.description  AS varchar) as origin,svl.description as reference,CAST (svl.quantity AS varchar)as usage,sl.complete_name
                                    ,(sm.location_id)as ubicacion,sm.write_uid as create_uid,sm.is_inventory as inventory_id,sm.picking_id 
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
     
    


class kardex_productos_inventario_detalle2(models.TransientModel):
    _name = 'kardex.productos.mov.detalle2'
    _description = "kardex productos"

    obj_kardex_mostrarmovi = fields.Many2one('kardex.productos.mov2')

    date = fields.Date(string='FECHA')
    date_cre=fields.Char(string='FECHA CRE')
    usuario= fields.Many2one('res.users',string='USUARIO')
    location_name=fields.Many2one('stock.location',string='BODEGA')
    concepto = fields.Char(string='DESCRIPCION')
    company_id = fields.Many2one('res.company', string='COMPANY')
    u_entrada = fields.Float()
    u_salida = fields.Float()
    u_saldo = fields.Float()
    costo_unit = fields.Float()
    v_entrada = fields.Float()
    v_salida = fields.Float()
    v_saldo = fields.Float()
    costo_prom = fields.Float()
    state = fields.Char(string='ESTADO')
    origin = fields.Char(string='ORIGEN')
    picking_id = fields.Many2one('stock.picking', string='PICKING')
    account_invoice = fields.Many2one('account.move', string='FACTURA')
    inventario = fields.Char(string='INVENTARIO')
    fact_supplier = fields.Char(string='FACTURA SUPPLIDOR')
    custumer_supplier = fields.Char(string='CLIENTE/PROVEEDOR')


class kardex_productos_inventario_conteo2(models.TransientModel):
    _name = 'kardex.productos.inventario.conteo2'
    _description = "Kardex  report conteo"

    detalle_conteo = fields.Integer(string='d_conbteo')
    #debe = fields.Float(string='Debit')   

# class kardex_add_user(models.Model):
#     _inherit = 'res.users' 

#     zonahoraria_kardex = fields.Char(string='Kardex Time Zone')
#     ver_costo= fields.Boolean(string='Admin', help="Allows the user to see the cost")
    
# class UserPartnerAcces(models.TransientModel):
#     _inherit = 'kardex.productos.mov'

     
#     def read(self, values):       
#         # Do your custom logic here
#         if self.env.user.ver_costo == False:
#             # error = self.env.user.login," Usted no tiene Permisos para Editar Clientes o Proveedores.\n Debe solicitar acceso en Configuración->Usuarios->Permisos Adicionales "
#              raise UserError("You do not have permission to view this module")
#         return super( UserPartnerAcces, self).read(values)

    # @api.model
    # def write(self, vals):
    #     if self.env.user.ver_costo == False:
    #         error = self.env.user.login," Usted no tiene Permisos para Editar Clientes o Proveedores.\n Debe solicitar acceso en Configuración->Usuarios->Permisos Adicionales "
    #         raise UserError(error)
    #     return super(UserPartnerAcces, self).write(vals)





