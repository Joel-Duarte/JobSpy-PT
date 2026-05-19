### Net-Empregos Parameters Configuration Reference

When scraping `Site.NET_EMPREGOS`, configure `ScraperInput` fields using backend option identifiers directly to bypass site parsing errors.

#### 1. Location (Zonas) Mappings
Pass the desired number string directly into the `location` field:
* `1`: Lisboa
* `2`: Porto
* `3`: Braga
* `4`: Aveiro
* `5`: Bragança
* `6`: Vila Real
* `7`: Guarda
* `8`: Viseu
* `9`: Coimbra
* `10`: Castelo Branco
* `11`: Leiria
* `12`: Santarém
* `13`: Setúbal
* `14`: Évora
* `15`: Beja
* `16`: Portalegre
* `17`: Faro
* `25`: Açores
* `26`: Madeira
* `28`: Viana do Castelo
* `0`: All Regions

#### 2. Categories Mappings
Append the category integer to the search text using a pipe separator (`|`) inside the `search_term` field (e.g., `search_term="Python|5"`):
* `1`: Telecomunicações
* `5`: Informática ( Programação )
* `6`: Indústria / Produção
* `8`: Comunicação Social / Media
* `9`: Hotelaria / Turismo
* `11`: Educação / Formação
* `12`: Imobiliário
* `14`: Saúde / Medicina / Enfermagem
* `15`: Contabilidade / Finanças
* `16`: Banca / Seguros / Serviços Financeiros
* `19`: Publicidade / Marketing
* `22`: Arquitectura / Design
* `23`: Construção Civil
* `24`: Engenharia ( Mecanica )
* `26`: Gestão de Empresas / Economia
* `29`: Administração / Secretariado
* `30`: Lojas / Comércio / Balcão
* `32`: Gestão RH
* `35`: Informática ( Internet )
* `36`: Informática ( Multimedia )
* `37`: Informática ( Gestão de Redes )
* `38`: Informática ( Analise de Sistemas )
* `42`: Restauração / Bares / Pastelarias
* `43`: Transportes / Logística
* `44`: Direito / Justiça
* `45`: Engenharia ( Civil )
* `46`: Engenharia ( Eletrotecnica )
* `49`: Informática ( Técnico de Hardware )
* `51`: Conservação / Manutenção / Técnica
* `53`: Comercial / Vendas
* `57`: Call Center / Help Desk