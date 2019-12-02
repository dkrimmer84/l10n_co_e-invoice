-- Actualiza configuración DIAN
   -- Actualiza datos de la empresa
update res_company
   set digital_certificate = '',
       issuer_name = 'C=CO, L=Bogota D.C., O=Andes SCD., OU=Division de certificacion entidad final, CN=CA ANDES SCD S.A. Clase II, emailAddress=info@andesscd.com.co',
       software_identification_code = 'bf3285d7-ab35-4340-8af7-59c106771914',
       password_environment = '8Hollywood',
       trade_name = 'Plastinorte S.A.S',
       serial_number = '7407950780564486506',
       in_use_dian_sequence = 20,
       document_repository =  '/etc/odoo/dian',
       software_pin = '85917',
       seed_code = 5000000,
       certificate_key = 'Zhx7KbK4ND'       
 where id = x;

  -- Actualiza datos de la secuencia
 update ir_sequence
    set prefix = 'SETP',
        use_dian_control = TRUE  
  where id = xx;

  -- Actualiza datos de la resolución
update ir_sequence_dian_resolution
   set resolution_number = '18760000001',
       number_from = 990000000,
       number_to = 995000000,
       number_next = 990000071,
       date_from = '2019-01-19',
       date_to = '2030-01-19',
       active_resolution = TRUE,
       technical_key = 'fc8eac422eba16e22ffd8c6f94b3f40a6e38162c'
 where id = xx
   and sequence_id = xx;
  
 