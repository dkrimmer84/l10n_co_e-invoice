-- Actualiza configuración DIAN
   -- Actualiza datos de la empresa
update res_company
   set digital_certificate = '',
       issuer_name = 'C=CO, L=Bogota D.C., O=Andes SCD., OU=Division de certificacion entidad final, CN=CA ANDES SCD S.A. Clase II, emailAddress=info@andesscd.com.co',
       software_identification_code = 'b28bc5bb-8a74-46a7-bb16-d3e25ca58358',
       password_environment = '8Hollywood',
       trade_name = 'Plastinorte S.A.S',
       serial_number = '7407950780564486506',
       in_use_dian_sequence = 20,
       document_repository =  '/etc/odoo/dian',
       software_pin = '8Odoo77',
       seed_code = 5000000,
       certificate_key = 'Zhx7KbK4ND'       
 where id = 1;

  -- Actualiza datos de la secuencia
 update ir_sequence
    set prefix = 'PRUE',
        use_dian_control = TRUE  
  where id = 20;

  -- Actualiza datos de la resolución
update ir_sequence_dian_resolution
   set resolution_number = '9000000032442243',
       number_from = 980000000,
       number_to = 985000000,
       number_next = 980000602,
       date_from = '2019-01-30',
       date_to = '2020-07-30',
       active_resolution = TRUE,
       technical_key = 'dd85db55545bd6566f36b0fd3be9fd8555c36e'
 where id = 47
   and sequence_id = 20;
  
 