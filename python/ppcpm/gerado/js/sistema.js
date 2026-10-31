
/* ===== IDIOMA E TEMA (Versão 31) =====
   Textos do sistema ficam em português no código. Para inglês e espanhol, cada texto é trocado por este dicionário
   (TX). DICT = texto exato; RXL = textos com números/nomes no meio. Os dados cadastrados (produtos, nomes) nunca são traduzidos. */
const UI_KEY='projeart_pcp:ui',HL={pt:'pt-BR',en:'en',es:'es'},LOC={pt:'pt-BR',en:'en-US',es:'es-ES'};
let LANG='pt',THEME='dark';
try{const u=JSON.parse(localStorage.getItem(UI_KEY));if(u){if(HL[u.idioma])LANG=u.idioma;if(u.tema==='light')THEME='light'}}catch(e){}
const Tf=(p,e,s)=>LANG==='en'?e:LANG==='es'?s:p;
const DICT=[
["se é pra fazer,","if it's worth doing,","si vale la pena hacerlo,"],
["faça bem feito !","do it right!","¡hazlo bien hecho!"],
["Sistema Operacional","Operations System","Sistema de Operaciones"],
["Sistema Operacional · Grupo Projeart","Operations System · Grupo Projeart","Sistema de Operaciones · Grupo Projeart"],
["SISTEMA - PPCPM","Operations System · Grupo Projeart · Version 31","Sistema de Operaciones · Grupo Projeart · Versión 31"],
["Versão 31","Version 31","Versión 31"],
["Planejamento e Controle da Produção","Production Planning and Control","Planificación y Control de la Producción"],
["Acesse com suas credenciais.","Sign in with your credentials.","Accede con tus credenciales."],
["LOGIN | NOME","USERNAME | NAME","USUARIO | NOMBRE"],["login | nome","username | name","usuario | nombre"],["LOGIN","USERNAME","USUARIO"],["Login","Username","Usuario"],["login","login","login"],["logout","logout","cierre de sesión"],
["SENHA","PASSWORD","CONTRASEÑA"],["E-MAIL","E-MAIL","CORREO"],["E-mail","E-mail","Correo"],
["Digite seu login","Enter your username","Escribe tu usuario"],
["Digite sua senha","Enter your password","Escribe tu contraseña"],
["Digite seu e-mail","Enter your e-mail","Escribe tu correo"],
["Mostrar senha","Show password","Mostrar contraseña"],["Ocultar senha","Hide password","Ocultar contraseña"],
["Salvar senha","Remember password","Recordar contraseña"],
["CADASTRE-SE","SIGN UP","REGÍSTRATE"],
["Criar cadastro para acessar o sistema","Create an account to access the system","Crear una cuenta para acceder al sistema"],
["ENTRAR","SIGN IN","ENTRAR"],
["ACESSO SEGURO · GRUPO PROJEART","SECURE ACCESS · GRUPO PROJEART","ACCESO SEGURO · GRUPO PROJEART"],
["Criar cadastro","Create account","Crear cuenta"],
["Solicite seu acesso ao sistema.","Request access to the system.","Solicita tu acceso al sistema."],
["O administrador vai analisar o seu pedido.","The administrator will review your request.","El administrador revisará tu solicitud."],
["NOME COMPLETO","FULL NAME","NOMBRE COMPLETO"],
["Digite seu nome e sobrenome","Enter your first and last name","Escribe tu nombre y apellido"],
["Ex.: joao.silva","E.g.: john.smith","Ej.: juan.perez"],
["Mínimo de 6 caracteres","At least 6 characters","Mínimo 6 caracteres"],
["CONFIRMAR SENHA","CONFIRM PASSWORD","CONFIRMAR CONTRASEÑA"],
["Digite a senha novamente","Enter the password again","Escribe la contraseña otra vez"],
["Cadastro enviado!","Request sent!","¡Solicitud enviada!"],
["Seu pedido foi registrado e o e-mail para o administrador foi aberto no seu programa de e-mail.","Your request was recorded and the e-mail to the administrator was opened in your mail app.","Tu solicitud fue registrada y el correo para el administrador se abrió en tu programa de correo."],
["Confira e clique em Enviar.","Check it and click Send.","Revísalo y haz clic en Enviar."],
["Você poderá entrar assim que o cadastro for aprovado.","You can sign in as soon as your registration is approved.","Podrás entrar en cuanto se apruebe tu registro."],
["Abrir e-mail ao administrador","Open e-mail to the administrator","Abrir correo al administrador"],
["Copiar mensagem","Copy message","Copiar mensaje"],
["Já foi aprovado? Ativar com o código de liberação","Already approved? Activate with the release code","¿Ya fue aprobado? Activar con el código de liberación"],
["Cole aqui o e-mail ou o código que começa com PJT-LIB:","Paste the e-mail or the code starting with PJT-LIB: here","Pega aquí el correo o el código que empieza con PJT-LIB:"],
["Ativar acesso","Activate access","Activar acceso"],
["← Voltar para o login","← Back to sign in","← Volver al inicio de sesión"],
["Aparência e idioma","Appearance and language","Apariencia e idioma"],
["Sair","Sign out","Salir"],["Menu","Menu","Menú"],
["Início","Home","Inicio"],["Produção","Production","Producción"],
["Ordens de Produção","Production Orders","Órdenes de Producción"],["Área de impressão","Print Area","Área de impresión"],["ÁREA DE IMPRESSÃO","PRINT AREA","ÁREA DE IMPRESIÓN"],
["Materiais / Estoque","Materials / Inventory","Materiales / Inventario"],
["Planejamento","Planning","Planificación"],["Capacidade","Capacity","Capacidad"],
["Qualidade / RNC","Quality / NCR","Calidad / NC"],["Indicadores","KPIs","Indicadores"],
["Relatórios","Reports","Informes"],["Usuários","Users","Usuarios"],["Configurações","Settings","Configuración"],
["Indústria Metalúrgica","Metalworking Industry","Industria Metalúrgica"],
["Produto","Product","Producto"],["Quantidade","Quantity","Cantidad"],["Produzido","Produced","Producido"],
["Apontar produção","Log production","Registrar producción"],
["Gire o anel: sentido horário soma peças, anti-horário tira. Giro rápido conta 10 vezes mais.","Turn the ring: clockwise adds pieces, counter-clockwise removes. A fast spin counts 10 times more.","Gira el anillo: sentido horario suma piezas, antihorario resta. Un giro rápido cuenta 10 veces más."],
["Peças por passo","Pieces per step","Piezas por paso"],
["Tirar um passo","Remove one step","Quitar un paso"],["Somar um passo","Add one step","Sumar un paso"],
["Completar OP","Complete PO","Completar OP"],
["Processo","Process","Proceso"],["Prazo","Deadline","Plazo"],["Status","Status","Estado"],
["Excluir","Delete","Eliminar"],["Cancelar","Cancel","Cancelar"],["Salvar","Save","Guardar"],
["Peças produzidas","Pieces produced","Piezas producidas"],
["Nova ordem de produção","New production order","Nueva orden de producción"],
["Corte","Cutting","Corte"],["Dobra","Bending","Doblado"],["Solda","Welding","Soldadura"],["Pintura","Painting","Pintura"],["Montagem","Assembly","Montaje"],
["Em aberto","Open","Abierta"],["Em produção","In production","En producción"],["Concluída","Completed","Concluida"],["Atrasada","Late","Atrasada"],["Em risco","At risk","En riesgo"],
["Visão geral do dia","Daily overview","Resumen del día"],
["Todos os processos","All processes","Todos los procesos"],["Todos os status","All statuses","Todos los estados"],
["OPs totais","Total POs","OPs totales"],["Produção realizada","Production completed","Producción realizada"],
["peças","pieces","piezas"],["Meta x realizado","Target vs actual","Meta vs realizado"],
["OPs atrasadas","Late POs","OPs atrasadas"],["OPs em risco","POs at risk","OPs en riesgo"],["OPs em aberto","Open POs","OPs abiertas"],
["vencem em até 2 dias","due within 2 days","vencen en hasta 2 días"],["aguardando início","waiting to start","esperando inicio"],
["Planejado x realizado por processo","Planned vs actual by process","Planificado vs realizado por proceso"],
["(azul planejado · verde realizado)","(blue planned · green actual)","(azul planificado · verde realizado)"],
["Status das OPs","PO status","Estado de las OPs"],["OPs","POs","OPs"],
["Carga x capacidade","Load vs capacity","Carga vs capacidad"],["(peças pendentes)","(pending pieces)","(piezas pendientes)"],
["OPs atrasadas / em risco","Late / at-risk POs","OPs atrasadas / en riesgo"],["Ordens em andamento","Orders in progress","Órdenes en curso"],
["OP","PO","OP"],["Qtde","Qty","Cant."],["Atraso","Delay","Retraso"],
["Nenhuma OP nesta lista.","No POs in this list.","Ninguna OP en esta lista."],
["Buscar por OP ou produto","Search by PO or product","Buscar por OP o producto"],["Buscar","Search","Buscar"],
["+ Nova OP","+ New PO","+ Nueva OP"],
["Planejamento · prazos de entrega","Planning · delivery deadlines","Planificación · plazos de entrega"],
["Mês anterior","Previous month","Mes anterior"],["Próximo mês","Next month","Mes siguiente"],
["Dom","Sun","Dom"],["Seg","Mon","Lun"],["Ter","Tue","Mar"],["Qua","Wed","Mié"],["Qui","Thu","Jue"],["Sex","Fri","Vie"],["Sáb","Sat","Sáb"],
["Este módulo chega em uma versão futura.","This module arrives in a future version.","Este módulo llega en una versión futura."],
["Diga o que ele precisa fazer e montamos o próximo.","Tell us what it needs to do and we'll build the next one.","Dinos qué necesita hacer y armamos el siguiente."],
["Banco de dados deste navegador","Database in this browser","Base de datos de este navegador"],
["Tudo o que você cadastra é salvo na hora, aqui no navegador, organizado em tabelas iguais às de um banco de dados. Quando o banco da empresa estiver pronto, use","Everything you register is saved instantly, here in the browser, organized in tables identical to a database's. When the company database is ready, use","Todo lo que registras se guarda al instante, aquí en el navegador, organizado en tablas iguales a las de una base de datos. Cuando la base de la empresa esté lista, usa"],
["e rode o arquivo no PostgreSQL ou Supabase.","and run the file in PostgreSQL or Supabase.","y ejecuta el archivo en PostgreSQL o Supabase."],
["Exportar para banco (SQL)","Export to database (SQL)","Exportar a base de datos (SQL)"],
["Exportar backup (JSON)","Export backup (JSON)","Exportar copia de seguridad (JSON)"],
["Importar backup","Import backup","Importar copia de seguridad"],
["Restaurar dados de exemplo","Restore sample data","Restaurar datos de ejemplo"],
["Ordens de produção","Production orders","Órdenes de producción"],["Apontamentos","Production logs","Registros de producción"],
["Histórico de ações","Action history","Historial de acciones"],["Solicitações de cadastro","Registration requests","Solicitudes de registro"],
["Preferências","Preferences","Preferencias"],
["Último salvamento","Last saved","Último guardado"],["· Espaço usado","· Space used","· Espacio usado"],
["Identificação deste computador","This computer's ID","Identificación de este equipo"],
["Aparência","Appearance","Apariencia"],["Tema","Theme","Tema"],["Idioma","Language","Idioma"],["Escuro","Dark","Oscuro"],["Claro","Light","Claro"],
["Mostrar a animação de abertura ao entrar no sistema","Show the opening animation when signing in","Mostrar la animación de apertura al entrar al sistema"],
["▶ Ver animação agora","▶ Watch animation now","▶ Ver animación ahora"],
["Últimas ações registradas","Latest recorded actions","Últimas acciones registradas"],
["Quando","When","Cuándo"],["Usuário","User","Usuario"],["Ação","Action","Acción"],["Registro","Record","Registro"],
["Nenhuma ação registrada ainda.","No actions recorded yet.","Ninguna acción registrada todavía."],
["Sobre o sistema","About the system","Acerca del sistema"],
["Módulos desta versão: Tela inicial, Ordens de Produção, Planejamento, Usuários e Configurações.","Modules in this version: Home, Production Orders, Planning, Users and Settings.","Módulos de esta versión: Inicio, Órdenes de Producción, Planificación, Usuarios y Configuración."],
["Previstos para a próxima versão: Produção, Materiais / Estoque, Capacidade, Qualidade / RNC, Indicadores e Relatórios.","Planned for the next version: Production, Materials / Inventory, Capacity, Quality / NCR, KPIs and Reports.","Previstos para la próxima versión: Producción, Materiales / Inventario, Capacidad, Calidad / NC, Indicadores e Informes."],
["editar","edit","editar"],["criar","create","crear"],["excluir","delete","eliminar"],["login_falhou","failed login","inicio fallido"],
["exportar_json","export JSON","exportar JSON"],["exportar_sql","export SQL","exportar SQL"],["importar_backup","import backup","importar copia"],
["restaurar_exemplo","restore sample data","restaurar datos de ejemplo"],["solicitar_cadastro","request registration","solicitar registro"],
["aprovar","approve","aprobar"],["recusar","reject","rechazar"],["bloquear","block","bloquear"],["desbloquear","unblock","desbloquear"],
["importar_pedido","import request","importar solicitud"],["ativar_por_codigo","activate by code","activar por código"],
["Usuários e cadastros","Users and registrations","Usuarios y registros"],
["Nome","Name","Nombre"],["Pedido em","Requested on","Solicitado el"],
["✓ Aprovar","✓ Approve","✓ Aprobar"],["✕ Recusar","✕ Reject","✕ Rechazar"],
["Nenhum pedido aguardando aprovação.","No requests awaiting approval.","Ninguna solicitud pendiente de aprobación."],
["Recebeu uma solicitação por e-mail?","Received a request by e-mail?","¿Recibiste una solicitud por correo?"],
["Copie a chave de acesso do e-mail (a sequência que começa com eyJ), cole abaixo e clique em Importar. O pedido aparece na lista acima para você aprovar. A chave vale por 5 minutos.","Copy the entire e-mail (or just the code starting with PJT-CAD:), paste it below and click Import. The request appears in the list above for you to approve.","Copia el correo completo (o solo el código que empieza con PJT-CAD:), pégalo abajo y haz clic en Importar. La solicitud aparece en la lista de arriba para que la apruebes."],
["Cole aqui a chave de acesso...","Paste the e-mail or the PJT-CAD: code here...","Pega aquí el correo o el código PJT-CAD:..."],
["Importar solicitação","Import request","Importar solicitud"],
["Último acesso","Last access","Último acceso"],["Situação","Status","Situación"],
["Administrador","Administrator","Administrador"],["Ativo","Active","Activo"],["Bloqueado","Blocked","Bloqueado"],
["Bloquear","Block","Bloquear"],["Desbloquear","Unblock","Desbloquear"],["Reenviar liberação","Resend release","Reenviar liberación"],
["Pedidos recusados recentes","Recently rejected requests","Solicitudes rechazadas recientes"],["Recusado em","Rejected on","Rechazado el"],
["Estoque","Inventory","Inventario"],["Qualidade","Quality","Calidad"],
["“Dados da produção conectados em um só lugar.”","“Production data connected in one place.”","“Datos de producción conectados en un solo lugar.”"],
["Iniciando…","Starting…","Iniciando…"],["Conectando estoque…","Connecting inventory…","Conectando inventario…"],
["Conectando ordens de produção…","Connecting production orders…","Conectando órdenes de producción…"],
["Conectando planejamento…","Connecting planning…","Conectando planificación…"],["Conectando capacidade…","Connecting capacity…","Conectando capacidad…"],
["Conectando qualidade…","Connecting quality…","Conectando calidad…"],["Conectando gestão de dados…","Connecting data management…","Conectando gestión de datos…"],["Gestão de Dados","Data Management","Gestión de Datos"],["Entrando no sistema…","Entering the system…","Entrando al sistema…"],
["Animação de abertura: dados da produção entrando no sistema","Opening animation: production data entering the system","Animación de apertura: datos de producción entrando al sistema"],
["Pular","Skip","Omitir"],
["nome","name","nombre"],["senha","password","contraseña"],["confirmar senha","confirm password","confirmar contraseña"],["e-mail","e-mail","correo"],
["Preencha todos os campos.","Fill in all fields.","Completa todos los campos."],
["E-mail inválido.","Invalid e-mail.","Correo no válido."],
["Digite um e-mail no formato nome@empresa.com.br.","Enter an e-mail in the format name@company.com.","Escribe un correo con el formato nombre@empresa.com."],
["Acesso bloqueado.","Access blocked.","Acceso bloqueado."],
["Seu usuário está bloqueado. Fale com o administrador do sistema.","Your user is blocked. Talk to the system administrator.","Tu usuario está bloqueado. Habla con el administrador del sistema."],
["Cadastro em análise.","Registration under review.","Registro en revisión."],
["Seu cadastro ainda está aguardando a aprovação do administrador.","Your registration is still waiting for the administrator's approval.","Tu registro aún espera la aprobación del administrador."],
["Cadastro não aprovado.","Registration not approved.","Registro no aprobado."],
["Seu pedido de acesso foi recusado. Fale com o administrador.","Your access request was rejected. Talk to the administrator.","Tu solicitud de acceso fue rechazada. Habla con el administrador."],
["Erro no login.","Sign-in error.","Error al iniciar sesión."],
["Login, senha ou e-mail incorretos. Confira os dados e tente de novo.","Incorrect username, password or e-mail. Check your details and try again.","Usuario, contraseña o correo incorrectos. Revisa los datos e inténtalo de nuevo."],
["Nome incompleto.","Incomplete name.","Nombre incompleto."],["Digite seu nome completo.","Enter your full name.","Escribe tu nombre completo."],
["Login inválido.","Invalid username.","Usuario no válido."],
["Use de 3 a 30 caracteres: letras sem acento, números, ponto, hífen ou sublinhado, sem espaços. Ex.: joao.silva","Use 3 to 30 characters: letters without accents, numbers, dot, hyphen or underscore, no spaces. E.g.: john.smith","Usa de 3 a 30 caracteres: letras sin acento, números, punto, guion o guion bajo, sin espacios. Ej.: juan.perez"],
["Login indisponível.","Username unavailable.","Usuario no disponible."],
["Esse login já existe ou já tem um pedido em análise. Escolha outro.","This username already exists or already has a request under review. Choose another.","Ese usuario ya existe o ya tiene una solicitud en revisión. Elige otro."],
["Senha muito curta.","Password too short.","Contraseña muy corta."],["A senha precisa ter pelo menos 6 caracteres.","The password must have at least 6 characters.","La contraseña debe tener al menos 6 caracteres."],
["As senhas não conferem.","Passwords do not match.","Las contraseñas no coinciden."],["Digite a mesma senha nos dois campos.","Enter the same password in both fields.","Escribe la misma contraseña en los dos campos."],
["Código inválido.","Invalid code.","Código no válido."],
["Cole o código completo que começa com PJT-LIB: e termina com :FIM.","Paste the full code that starts with PJT-LIB: and ends with :FIM.","Pega el código completo que empieza con PJT-LIB: y termina con :FIM."],
["Acesso ativado! Digite sua senha e clique em Entrar.","Access activated! Enter your password and click Sign in.","¡Acceso activado! Escribe tu contraseña y haz clic en Entrar."],
["Não foi possível copiar","Could not copy","No se pudo copiar"],
["Não foi possível salvar: armazenamento do navegador cheio ou bloqueado. Exporte um backup.","Could not save: browser storage is full or blocked. Export a backup.","No se pudo guardar: el almacenamiento del navegador está lleno o bloqueado. Exporta una copia de seguridad."],
["Animação de abertura ligada","Opening animation on","Animación de apertura activada"],["Animação de abertura desligada","Opening animation off","Animación de apertura desactivada"],
["Dados de exemplo restaurados","Sample data restored","Datos de ejemplo restaurados"],
["Apagar todas as OPs e voltar aos dados de exemplo?","Delete all POs and go back to the sample data?","¿Borrar todas las OPs y volver a los datos de ejemplo?"],
["Backup exportado","Backup exported","Copia de seguridad exportada"],["Arquivo SQL exportado","SQL file exported","Archivo SQL exportado"],
["Backup importado","Backup imported","Copia de seguridad importada"],
["Arquivo inválido. Use um backup exportado por este sistema.","Invalid file. Use a backup exported by this system.","Archivo no válido. Usa una copia de seguridad exportada por este sistema."],
["Cadastro recusado","Registration rejected","Registro rechazado"],
["Essa solicitação já foi importada.","This request was already imported.","Esta solicitud ya fue importada."],
["Código não reconhecido. Cole o código completo, de PJT-CAD: até :FIM.","Code not recognized. Paste the full code, from PJT-CAD: to :FIM.","Código no reconocido. Pega el código completo, de PJT-CAD: hasta :FIM."],
["Preencha produto, quantidade e prazo","Fill in product, quantity and deadline","Completa producto, cantidad y plazo"],
["OP excluída","PO deleted","OP eliminada"],["OP salva","PO saved","OP guardada"],
["Cadastro realizado","Registration completed","Registro realizado"],
["Aguarde o administrador enviar a chave de acesso por e-mail ou por outro meio de comunicação.","Wait for the administrator to send the access key by e-mail or another means of communication.","Espera a que el administrador envíe la clave de acceso por correo u otro medio de comunicación."],
["Confira o e-mail aberto para o administrador e clique em Enviar.","Check the e-mail opened for the administrator and click Send.","Revisa el correo abierto para el administrador y haz clic en Enviar."],
["% Porcentagem impresso","% Printed","% Impreso"],["Total já realizados","Total completed","Total ya realizados"],["Obras para impressão","Jobs to print","Obras para impresión"],["Obras impressas","Printed jobs","Obras impresas"],["Obras pendente","Pending jobs","Obras pendientes"],
["Tempo restante para ativar:","Time left to activate:","Tiempo restante para activar:"],
["Código expirado","Code expired","Código caducado"],
["Código expirado.","Code expired.","Código caducado."],
["O prazo de 5 minutos terminou. Faça um novo cadastro.","The 5-minute limit has ended. Please register again.","El plazo de 5 minutos terminó. Haz un nuevo registro."],
["O prazo de 5 minutos acabou. Toque em CADASTRE-SE e refaça o cadastro.","The 5-minute limit is over. Tap SIGN UP and register again.","El plazo de 5 minutos terminó. Toca REGÍSTRATE y vuelve a registrarte."],
["Refazer cadastro","Register again","Volver a registrarse"],
["Recebeu a chave de acesso? Ativar acesso","Received the access key? Activate access","¿Recibiste la clave de acceso? Activar acceso"],
["Cole aqui a chave de acesso enviada pelo administrador","Paste here the access key sent by the administrator","Pega aquí la clave de acceso enviada por el administrador"],
["Chave inválida.","Invalid key.","Clave no válida."],
["Cole a chave de acesso completa que você recebeu por e-mail.","Paste the full access key you received by e-mail.","Pega la clave de acceso completa que recibiste por correo."],
["E-mail não autorizado.","E-mail not authorized.","Correo no autorizado."],
["Use seu e-mail corporativo, terminado em @projeart.ind.br.","Use your corporate e-mail, ending in @projeart.ind.br.","Usa tu correo corporativo, terminado en @projeart.ind.br."],
["Esse login já está em uso por outra conta.","This username is already used by another account.","Ese usuario ya está en uso por otra cuenta."],
["Login indisponível.","Username unavailable.","Usuario no disponible."],
["Chave expirada: o usuário precisa refazer o cadastro.","Key expired: the user must register again.","Clave caducada: el usuario debe volver a registrarse."],
["Chave não reconhecida. Cole a chave de acesso completa recebida por e-mail.","Key not recognized. Paste the full access key received by e-mail.","Clave no reconocida. Pega la clave de acceso completa recibida por correo."],
["Copie a chave de acesso do e-mail (a sequência que começa com eyJ), cole abaixo e clique em Importar. O pedido aparece na lista acima para você aprovar. A chave vale por 5 minutos.","Copy the access key from the e-mail (the sequence starting with eyJ), paste it below and click Import. The request appears in the list above for you to approve. The key is valid for 5 minutes.","Copia la clave de acceso del correo (la secuencia que empieza con eyJ), pégala abajo y haz clic en Importar. La solicitud aparece en la lista de arriba para que la apruebes. La clave vale 5 minutos."],
["Cole aqui a chave de acesso...","Paste the access key here...","Pega aquí la clave de acceso..."],
["Este módulo chega em uma versão futura.","This module arrives in a future version.","Este módulo llega en una versión futura."],
["expirado","expired","caducado"]
,
["O administrador já recebeu a chave por e-mail automaticamente.","The administrator has automatically received the key by e-mail.","El administrador ya recibió la clave por correo automáticamente."],
["Banco de dados na nuvem","Cloud database","Base de datos en la nube"],
["Tudo o que você cadastra é salvo na hora no servidor privado da empresa (Supabase). Só usuários ativos e autenticados conseguem ver os dados.","Everything you register is saved instantly on the company's private server (Supabase). Only active, signed-in users can see the data.","Todo lo que registras se guarda al instante en el servidor privado de la empresa (Supabase). Solo los usuarios activos y autenticados pueden ver los datos."],
["Última atualização","Last update","Última actualización"],
["Conexão","Connection","Conexión"],
["online","online","en línea"],
["sem conexão","offline","sin conexión"],
["Sem conexão com o servidor","No connection to the server","Sin conexión con el servidor"],
["Sem conexão com o servidor.","No connection to the server.","Sin conexión con el servidor."],
["Confira a internet e tente de novo.","Check your internet and try again.","Revisa tu internet e inténtalo de nuevo."],
["Não foi possível falar com o servidor. Confira a internet e tente de novo.","Could not reach the server. Check your internet and try again.","No se pudo conectar con el servidor. Revisa tu internet e inténtalo de nuevo."],
["Você não tem permissão para fazer isso.","You do not have permission to do that.","No tienes permiso para hacer eso."],
["Acesso ainda não ativado.","Access not activated yet.","Acceso aún no activado."],
["Use a chave de acesso enviada pelo administrador (CADASTRE-SE › Ativar acesso). Se já passaram 5 minutos, refaça o cadastro.","Use the access key sent by the administrator (SIGN UP › Activate access). If 5 minutes have passed, register again.","Usa la clave de acceso enviada por el administrador (REGÍSTRATE › Activar acceso). Si pasaron 5 minutos, repite el registro."],
["Acesso bloqueado.","Access blocked.","Acceso bloqueado."],
["Seu usuário está bloqueado. Fale com o administrador do sistema.","Your user is blocked. Talk to the system administrator.","Tu usuario está bloqueado. Habla con el administrador del sistema."],
["Senha inválida.","Invalid password.","Contraseña inválida."],
["A senha precisa ter de 6 a 72 caracteres.","The password must be 6 to 72 characters long.","La contraseña debe tener de 6 a 72 caracteres."],
["E-mail já cadastrado.","E-mail already registered.","Correo ya registrado."],
["Esse e-mail já tem um cadastro. Se foi há mais de 5 minutos sem ativar, aguarde um instante e tente de novo.","This e-mail already has a registration. If it was over 5 minutes ago without activating, wait a moment and try again.","Este correo ya tiene un registro. Si fue hace más de 5 minutos sin activar, espera un momento e inténtalo de nuevo."],
["Muitos pedidos.","Too many requests.","Demasiadas solicitudes."],
["Muitos cadastros em pouco tempo. Aguarde alguns minutos e tente de novo.","Too many registrations in a short time. Wait a few minutes and try again.","Demasiados registros en poco tiempo. Espera unos minutos e inténtalo de nuevo."],
["Não foi possível avisar o administrador.","Could not notify the administrator.","No se pudo avisar al administrador."],
["O e-mail para o administrador não pôde ser enviado. Tente de novo em instantes.","The e-mail to the administrator could not be sent. Try again shortly.","No se pudo enviar el correo al administrador. Inténtalo de nuevo en unos instantes."],
["Não foi possível cadastrar.","Could not register.","No se pudo registrar."],
["Tente de novo em instantes.","Try again shortly.","Inténtalo de nuevo en unos instantes."],
["Aguardando chave","Awaiting key","Esperando clave"],
["Ativado","Activated","Activado"],
["Expirado","Expired","Expirado"],
["Recusado","Declined","Rechazado"],
["Vale até","Valid until","Válida hasta"],
["Perfil","Profile","Perfil"],
["Pedidos recentes","Recent requests","Solicitudes recientes"],
["A chave de acesso chega no seu e-mail. Para aprovar, clique em Aprovar agora (mais simples) ou envie a chave ao e-mail corporativo da pessoa em até 5 minutos.","The access key arrives in your e-mail. To approve, send the key to the person's corporate e-mail within 5 minutes.","La clave de acceso llega a tu correo. Para aprobar, envía la clave al correo corporativo de la persona en hasta 5 minutos."],
["Ações registradas (últimas)","Logged actions (latest)","Acciones registradas (últimas)"],
["Carregar OPs de exemplo","Load sample OPs","Cargar OP de ejemplo"],
["Dados de exemplo carregados","Sample data loaded","Datos de ejemplo cargados"],
["Exportar backup (JSON)","Export backup (JSON)","Exportar copia (JSON)"]
,
["✓ Aprovar agora","✓ Approve now","✓ Aprobar ahora"],
["A chave de acesso chega no seu e-mail. Para aprovar, clique em Aprovar agora (mais simples) ou envie a chave ao e-mail corporativo da pessoa em até 5 minutos.","The access key arrives in your e-mail. To approve, click Approve now (simpler) or send the key to the person's corporate e-mail within 5 minutes.","La clave de acceso llega a tu correo. Para aprobar, haz clic en Aprobar ahora (más simple) o envía la clave al correo corporativo de la persona en hasta 5 minutos."],
["Esse pedido já expirou: a pessoa precisa refazer o cadastro.","This request has expired: the person must register again.","Esta solicitud ya expiró: la persona debe registrarse de nuevo."],
["Não foi possível aprovar agora. Tente de novo.","Could not approve now. Try again.","No se pudo aprobar ahora. Inténtalo de nuevo."]
,
["desenvolvido por","developed by","desarrollado por"]
,
["(opção só do administrador)","(administrator-only option)","(opción solo del administrador)"],
["A animação de abertura é obrigatória ao entrar no sistema.","The opening animation is mandatory when entering the system.","La animación de apertura es obligatoria al entrar en el sistema."]
,
["Tela inicial","Home","Pantalla de inicio"],
["Módulos desta versão: Tela inicial, Ordens de Produção, Planejamento, Usuários e Configurações.","Modules in this version: Home, Production Orders, Planning, Users and Settings.","Módulos de esta versión: Pantalla de inicio, Órdenes de Producción, Planificación, Usuarios y Configuración."],
["Tema claro","Light theme","Tema claro"],
["Tema escuro","Dark theme","Tema oscuro"]
,
["Mudar para o tema claro","Switch to light theme","Cambiar al tema claro"],
["Mudar para o tema escuro","Switch to dark theme","Cambiar al tema oscuro"],
["Mudar tema","Change theme","Cambiar tema"]
];
const RXL=[
[/^(.+) aprovado\(a\)\. Avise a pessoa: ela já pode entrar com login, e-mail e senha\.$/,"$1 approved. Tell the person: they can now sign in with login, e-mail and password.","$1 aprobado(a). Avisa a la persona: ya puede entrar con login, correo y contraseña."],
[/^Editar (OP-\d+)$/,"Edit $1","Editar $1"],
[/^Excluir (OP-\d+)\?$/,"Delete $1?","¿Eliminar $1?"],
[/^(\d+) concluídas · (\d+) em produção$/,"$1 completed · $2 in production","$1 concluidas · $2 en producción"],
[/^meta: (.+) peças$/,"target: $1 pieces","meta: $1 piezas"],
[/^(\d+)% do total$/,"$1% of total","$1% del total"],
[/^(\d+) OP\(s\)\. Toque numa linha para apontar produção ou editar\.$/,"$1 PO(s). Tap a row to log production or edit.","$1 OP(s). Toca una fila para registrar producción o editar."],
[/^Sistema online · dados salvos neste navegador · (.+)$/,"System online · data saved in this browser · $T1","Sistema en línea · datos guardados en este navegador · $T1"],
[/^(Sistema online|Sem conexão com o servidor) · dados salvos no servidor · (.+)$/,"$T1 · data saved on the server · $T2","$T1 · datos guardados en el servidor · $T2"],
[/^Último salvamento: (.+)$/,"Last saved: $1","Último guardado: $1"],
[/^· (Versão \d+)$/,"· $T1","· $T1"],
[/^· Estrutura v(\d+)$/,"· Schema v$1","· Estructura v$1"],
[/^Solicitações pendentes \((\d+)\)$/,"Pending requests ($1)","Solicitudes pendientes ($1)"],
[/^Usuários com acesso \((\d+)\)$/,"Users with access ($1)","Usuarios con acceso ($1)"],
[/^Falta preencher: (.*)\.$/,"Missing: $L1.","Falta completar: $L1."],
[/^Login, senha ou e-mail incorretos\. Confira os dados e tente de novo\. Tentativa (\d+)\.$/,"Incorrect username, password or e-mail. Check your details and try again. Attempt $1.","Usuario, contraseña o correo incorrectos. Revisa los datos e inténtalo de nuevo. Intento $1."],
[/^Mensagem copiada\. Cole no seu e-mail e envie para (.+)$/,"Message copied. Paste it in your e-mail and send it to $1","Mensaje copiado. Pégalo en tu correo y envíalo a $1"],
[/^Já existe um usuário com o login (.+)$/,"A user with username $1 already exists","Ya existe un usuario con el usuario $1"],
[/^O login (.+) já está em uso ou com pedido pendente\.$/,"The username $1 is already in use or has a pending request.","El usuario $1 ya está en uso o tiene una solicitud pendiente."],
[/^Solicitação de (.+) importada$/,"Request from $1 imported","Solicitud de $1 importada"],
[/^(.+) aprovado\(a\)\. Envie a chave de acesso para ele\(a\) entrar\.$/,"$1 approved. Send the access key so they can sign in.","$1 aprobado(a). Envía la clave de acceso para que pueda entrar."],
[/^(.+) desbloqueado\(a\)$/,"$1 unblocked","$1 desbloqueado(a)"],
[/^(.+) bloqueado\(a\)$/,"$1 blocked","$1 bloqueado(a)"],
[/^Recusar o cadastro de (.+) \((.+)\)\?$/,"Reject the registration of $1 ($2)?","¿Rechazar el registro de $1 ($2)?"],
[/^Cadastro aprovado![\s\S]*?enviar a chave de acesso para (.+) \((.+)\)\?$/,"Registration approved!\n\nOpen an e-mail to send the access key to $1 ($2)?","¡Registro aprobado!\n\n¿Abrir un correo para enviar la clave de acceso a $1 ($2)?"]
];
const I18N=new Map(DICT.map(d=>[d[0],{en:d[1],es:d[2]}]));
function lookupTX(k){const h=I18N.get(k);if(h)return h[LANG];
 if(k.endsWith(':')){const h2=I18N.get(k.slice(0,-1));if(h2)return h2[LANG]+':'}
 for(const x of RXL){const m=k.match(x[0]);if(m)return x[LANG==='en'?1:2].replace(/\$(T|L)?(\d)/g,(_,f,i)=>{const g=m[i]??'';return f==='T'?TX(g):f==='L'?g.split(', ').map(TX).join(', '):g})}
 return null}
function TX(s){if(LANG==='pt'||typeof s!=='string')return s;const k=s.trim();if(!k)return s;const r=lookupTX(k);if(r===null)return s;const i=s.indexOf(k);return s.slice(0,i)+r+s.slice(i+k.length)}
const NO=new WeakMap(),AO=new WeakMap(),ATT=['placeholder','aria-label','title','alt'];
function applyI18n(root){root=root||document.body;if(!root)return;
 const w=document.createTreeWalker(root,NodeFilter.SHOW_TEXT,{acceptNode:n=>/^(SCRIPT|STYLE|TEXTAREA)$/.test(n.parentNode.nodeName)?NodeFilter.FILTER_REJECT:NodeFilter.FILTER_ACCEPT}),ns=[];
 while(w.nextNode())ns.push(w.currentNode);
 for(const n of ns){let r=NO.get(n);if(!r||n.data!==r.l)r={o:n.data,l:n.data};const t=TX(r.o);if(t!==n.data)n.data=t;r.l=n.data;NO.set(n,r)}
 const els=[...root.querySelectorAll('[placeholder],[aria-label],[title],[alt]')];if(root.getAttribute&&ATT.some(a=>root.hasAttribute(a)))els.push(root);
 for(const el of els){let m=AO.get(el);if(!m){m={};AO.set(el,m)}
  for(const a of ATT){if(!el.hasAttribute(a))continue;const cur=el.getAttribute(a);let r=m[a];if(!r||cur!==r.l)r={o:cur,l:cur};const t=TX(r.o);if(t!==cur)el.setAttribute(a,t);r.l=t;m[a]=r}}}
function saveUI(){try{localStorage.setItem(UI_KEY,JSON.stringify({tema:THEME,idioma:LANG}))}catch(e){}}
const SUN_SVG='<svg class="ic" viewBox="0 0 24 24" aria-hidden="true"><circle cx="12" cy="12" r="4.3"/><path d="M12 2.6v2.6M12 18.8v2.6M2.6 12h2.6M18.8 12h2.6M5.4 5.4l1.8 1.8M16.8 16.8l1.8 1.8M5.4 18.6l1.8-1.8M16.8 7.2l1.8-1.8"/></svg>',MOON_SVG='<svg class="ic" viewBox="0 0 24 24" aria-hidden="true"><path d="M20.5 14.6A8.4 8.4 0 1 1 9.4 3.5a6.7 6.7 0 0 0 11.1 11.1z"/></svg>';
function markUI(){const t1=document.getElementById('tt1');if(t1){t1.innerHTML=THEME==='dark'?SUN_SVG:MOON_SVG;const tx=THEME==='dark'?'Mudar para o tema claro':'Mudar para o tema escuro';t1.title=TX(tx);t1.setAttribute('aria-label',TX(tx))}document.querySelectorAll('[data-th]').forEach(b=>{const on=b.dataset.th===THEME;b.classList.toggle('on',on);b.setAttribute('aria-pressed',on)});
 document.querySelectorAll('[data-lg]').forEach(b=>{const on=b.dataset.lg===LANG;b.classList.toggle('on',on);b.setAttribute('aria-pressed',on)})}
function setTheme(t){THEME=t==='light'?'light':'dark';document.documentElement.setAttribute('data-theme',THEME);saveUI();markUI()}
function setLang(l){if(!HL[l])return;LANG=l;saveUI();document.documentElement.lang=HL[l];limpaErro();cLimpa();document.title=TX('SISTEMA - PPCPM');applyI18n();clock();
 if(USER){setUserLabel();render()}else markUI()}
function pop(on){const p=$('#gp'),b=$('#gb'),v=on===undefined?p.classList.contains('hide'):on;p.classList.toggle('hide',!v);b.setAttribute('aria-expanded',v)}

const $=(s,e=document)=>e.querySelector(s),KEY='projeart_pcp_ops_v1',PROC=['Corte','Dobra','Solda','Pintura','Montagem'],CAP={Corte:6000,Dobra:5000,Solda:4500,Pintura:4000,Montagem:3500},STS=['Em aberto','Em produção','Concluída'];
const COL={'Em produção':'#2b8cff','Concluída':'#22c55e','Atrasada':'#ef4444','Em aberto':'#8fa6cf','Em risco':'#f5b301'};
const VERSAO='Versão 112';const PROG=[["pg1", "Análise da DBF X Focco - ERP", "PPCPM - ANÁLISE DBF × FOCCO ERP"], ["pg2", "Agrupador | Base", "PPCPM - AGRUPADOR | BASE"], ["pg3", "Roteirização produção", "PPCPM - ROTEIRIZAÇÃO DE PRODUÇÃO"], ["pg4", "Impressão Casada - ERP", "PPCPM - IMPRESSÃO CASADA - ERP"], ["pg5", "Impressão Casada | Multi obra", "PPCPM - IMPRESSÃO CASADA | MULTI OBRA"], ["pg6", "Impressão Grupo - LIC", "PPCPM - IMPRESSÃO GRUPO - LIC"], ["pg7", "Impressão - FLUXO 04", "PPCPM - IMPRESSÃO - FLUXO 04"], ["pg8", "Validação de Peso | Análise", "PPCPM - VALIDAÇÃO DE PESO | ANÁLISE"], ["pg10", "Alteração de Roteiros", "PPCPM - ALTERAÇÃO DE ROTEIROS"], ["pg11", "Acesso ao Intranet", "PPCPM - ACESSO AO INTRANET"], ["pg12", "Impressão de Etiquetas", "PPCPM - IMPRESSÃO DE ETIQUETAS"]];const PACOTE_ATUAL=694;const OBRA_IMPRESSAO='2139-5-01';
const iso=d=>d.getFullYear()+'-'+String(d.getMonth()+1).padStart(2,'0')+'-'+String(d.getDate()).padStart(2,'0');
const addD=n=>{const d=new Date();d.setDate(d.getDate()+n);return iso(d)},today=()=>iso(new Date());
const fd=s=>s.split('-').reverse().slice(0,2).join('/'),sum=(a,k)=>a.reduce((s,o)=>s+(+o[k]||0),0),nf=n=>Math.round(n).toLocaleString(LOC[LANG],{useGrouping:'always'});
const esc=s=>String(s).replace(/[&<>"']/g,c=>({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[c]));
function seed(){return[['Estrutura Metálica',1200,'Solda',-3,700,'Em produção'],['Suporte Industrial',800,'Pintura',3,300,'Em produção'],['Base Equipamento',500,'Dobra',-2,150,'Em produção'],['Perfil Estrutural',1000,'Corte',1,600,'Em produção'],['Chapa Metálica',600,'Montagem',5,0,'Em aberto'],['Suporte',900,'Solda',-5,200,'Em produção'],['Peça Especial',400,'Pintura',2,100,'Em produção'],['Viga Treliçada',1500,'Corte',6,0,'Em aberto'],['Pilar Metálico',700,'Dobra',8,0,'Em aberto'],['Terça Galvanizada',2000,'Corte',-1,2000,'Concluída'],['Guarda-corpo',350,'Montagem',-4,350,'Concluída']].map((r,i)=>({id:'OP-'+(1050+i),produto:r[0],qtde:r[1],proc:r[2],prazo:addD(r[3]),feito:r[4],st:r[5]}))}
/* ===== BANCO DE DADOS LOCAL =====
   Cada tabela fica salva separada no navegador (localStorage), com id, datas e usuário em cada registro.
   A estrutura (TAB) é a mesma das tabelas do banco: em Configurações dá para exportar em SQL (PostgreSQL/Supabase)
   ou JSON. Para ligar um banco real depois, basta trocar get/put por chamadas à API, sem mexer nas telas. */
let USER=null,ops=[],lastSync=null,OFF=false;
const SB_URL='https://zlbgiodxpywrqapjlldg.supabase.co',SB_KEY='sb_publishable_mYX9vBcW3BQnjZYnnrMmhA_EDWpzHQA';
const _mem={},AS={getItem:k=>{try{return sessionStorage.getItem(k)}catch(e){return _mem[k]??null}},setItem:(k,v)=>{try{sessionStorage.setItem(k,v)}catch(e){_mem[k]=v}},removeItem:k=>{try{sessionStorage.removeItem(k)}catch(e){delete _mem[k]}}};
let SB=null;try{SB=window.supabase.createClient(SB_URL,SB_KEY,{auth:{storage:AS,persistSession:true,autoRefreshToken:true,detectSessionInUrl:false}})}catch(e){console.error(e)}
const DB=(()=>{
 const C={perfis:[],solicitacoes:[],historico:[],nAp:0},now=()=>new Date().toISOString();
 async function refresh(){if(!USER||!SB)return false;
  try{const q=[SB.from('ops').select('*').order('id'),SB.from('perfis').select('*').order('criado_em')];
   if(USER.adm)q.push(SB.from('solicitacoes').select('*').order('solicitado_em',{ascending:false}).limit(50),SB.from('historico').select('*').order('em',{ascending:false}).limit(8),SB.from('apontamentos').select('id',{count:'exact',head:true}));
   const r=await Promise.all(q);if(r.some(x=>x.error))throw r.find(x=>x.error).error;
   ops=r[0].data;C.perfis=r[1].data;if(USER.adm){C.solicitacoes=r[2].data;C.historico=r[3].data;C.nAp=r[4].count||0}
   lastSync=now();OFF=false;return true}catch(e){console.error(e);OFF=true;return false}}
 return{now,refresh,get:t=>C[t]||[],nAp:()=>C.nAp,meta:()=>({atualizado_em:lastSync}),
  log(tabela,registro_id,acao,detalhes){if(!SB||!USER)return;SB.from('historico').insert({tabela,registro_id:registro_id==null?null:String(registro_id),acao,detalhes:detalhes||null}).then(()=>{},()=>{})}}})();
function falha(e){console.error(e);toast(e&&e.code==='42501'?'Você não tem permissão para fazer isso.':'Não foi possível falar com o servidor. Confira a internet e tente de novo.')}
let _pt=null;
function savePrefs(){if(!USER||!SB)return;clearTimeout(_pt);_pt=setTimeout(()=>{SB.from('preferencias').upsert({usuario:USER.id,valor:{filtros:{p:F.p,s:F.s,q:F.q},tela:cur,mes:iso(CM),passo:Dial.getStep(),anim:ANIM},atualizado_em:DB.now()}).then(()=>{},()=>{})},600)}
async function loadPrefs(){let v={};try{const r=await SB.from('preferencias').select('valor').maybeSingle();v=(r.data&&r.data.valor)||{}}catch(e){}
 if(v.filtros)Object.assign(F,v.filtros);if(v.mes){const d=new Date(v.mes+'T00:00');if(!isNaN(d)){CM=d;CM.setDate(1)}}if(v.passo)Dial.setStep(v.passo);ANIM=USER&&USER.adm?v.anim!==false:true;return v.tela&&(NAV.some(n=>n[0]===v.tela)||PROG.some(p=>p[0]===v.tela))?v.tela:'home'}
const hm=iso=>iso?new Date(iso).toLocaleString(LOC[LANG],{day:'2-digit',month:'2-digit',year:'numeric',hour:'2-digit',minute:'2-digit'}):'—';
const stat=o=>o.st==='Concluída'?o.st:(o.prazo<today()?'Atrasada':o.st),risk=o=>o.st!=='Concluída'&&o.prazo>=today()&&o.prazo<=addD(2);
const bd=o=>{const s=risk(o)?'Em risco':stat(o);return`<span class="b" style="--c:${COL[s]}">${s}</span>`};
const confirmT=m=>confirm(TX(m)),alertT=m=>alert(TX(m));
function toast(m){const t=document.createElement('div');t.id='toast';t.textContent=TX(m);document.body.append(t);setTimeout(()=>t.remove(),2200)}

$('#lg2').src=$('#lg1').src;

/* ===== CADASTRO DE USUÁRIOS (aprovação do administrador) ===== */
const sha256=(()=>{const K=[],P=[];for(let n=2;P.length<64;n++)if(P.every(p=>n%p))P.push(n);P.forEach(p=>K.push((Math.cbrt(p)%1)*2**32>>>0));
 return str=>{const b=new TextEncoder().encode(str),l=b.length,n=((l+9+63)>>6)<<6,m=new Uint8Array(n);m.set(b);m[l]=128;const dv=new DataView(m.buffer);dv.setUint32(n-4,l*8);
  let H=[0x6a09e667,0xbb67ae85,0x3c6ef372,0xa54ff53a,0x510e527f,0x9b05688c,0x1f83d9ab,0x5be0cd19];const w=new Int32Array(64),r=(x,k)=>x>>>k|x<<32-k;
  for(let i=0;i<n;i+=64){for(let t=0;t<16;t++)w[t]=dv.getUint32(i+t*4);for(let t=16;t<64;t++){const a=w[t-15],c=w[t-2];w[t]=w[t-16]+(r(a,7)^r(a,18)^a>>>3)+w[t-7]+(r(c,17)^r(c,19)^c>>>10)|0}
   let[a,bb,c,d,e,f,g,h]=H;for(let t=0;t<64;t++){const T1=h+(r(e,6)^r(e,11)^r(e,25))+(e&f^~e&g)+K[t]+w[t]|0,T2=(r(a,2)^r(a,13)^r(a,22))+(a&bb^a&c^bb&c)|0;h=g;g=f;f=e;e=d+T1|0;d=c;c=bb;bb=a;a=T1+T2|0}
   H=[a,bb,c,d,e,f,g,h].map((v,j)=>H[j]+v|0)}return H.map(v=>(v>>>0).toString(16).padStart(8,'0')).join('')}})();
const EMAIL_OK=/^[^\s@]+@[^\s@]+\.[^\s@]+$/,b64e=o=>btoa(unescape(encodeURIComponent(JSON.stringify(o)))),b64d=t=>JSON.parse(decodeURIComponent(escape(atob(t))));
const salGerar=()=>[...crypto.getRandomValues(new Uint8Array(12))].map(x=>x.toString(16).padStart(2,'0')).join('');
const uObj=p=>({id:p.id,l:p.login,n:p.nome||p.login,e:p.email,r:p.perfil||'Usuário',adm:!!p.admin});

const vencida=r=>!r||!r.expira_em||Date.now()>Date.parse(r.expira_em);
async function chamar(acao,corpo,tok){try{const h={'Content-Type':'application/json',apikey:SB_KEY};if(tok)h.Authorization='Bearer '+tok;const r=await fetch(SB_URL+'/functions/v1/cadastro',{method:'POST',headers:h,body:JSON.stringify({acao,...corpo})});const j=await r.json();return j&&typeof j==='object'?j:{erro:'erro_interno'}}catch(e){return{erro:'rede'}}}
async function chamarRetry(acao,corpo,tok){let r=await chamar(acao,corpo,tok);if(r.erro==='rede'||r.erro==='erro_interno'){await new Promise(z=>setTimeout(z,1500));r=await chamar(acao,corpo,tok)}return r}
const CK='projeart_pcp:cad';let ULT=null,CT=null;
function ultSet(u){ULT=u;try{u?localStorage.setItem(CK,JSON.stringify(u)):localStorage.removeItem(CK)}catch(e){}}
try{ULT=JSON.parse(localStorage.getItem(CK))}catch(e){}
const CN={'#cu':'login | nome','#cp':'senha','#cp2':'confirmar senha','#ce':'e-mail'};
function cLimpa(){$('#cer').innerHTML='';document.querySelectorAll('#cf .in').forEach(x=>x.classList.remove('bad'))}
function cErro(t,m,campos,foco){cLimpa();t=TX(t);m=TX(m);$('#cer').innerHTML=ico('warn')+'<span><b>'+t+'</b>'+m+'</span>';campos.forEach(c=>$(c).closest('.in').classList.add('bad'));
 const c=$('#cf');c.classList.remove('shk');void c.offsetWidth;c.classList.add('shk');$(foco||campos[0]).focus()}
function lErro(t,m){$('#clerr').innerHTML=t?ico('warn')+'<span><b>'+TX(t)+'</b>'+TX(m)+'</span>':''}
function vForm(){clearInterval(CT);CT=null;$('#cok').classList.add('hide');$('#cexp').classList.add('hide');$('#cfx').classList.remove('hide');$('.lib').classList.remove('hide');cLimpa();lErro()}
function vOk(){$('#cr1').textContent=(ULT&&ULT.login)||'—';$('#cr2').textContent=(ULT&&ULT.email)||'—';$('#cfx').classList.add('hide');$('#cexp').classList.add('hide');$('#cok').classList.remove('hide');$('.lib').classList.remove('hide');lErro();$('.lib').open=true;ctick();clearInterval(CT);CT=setInterval(ctick,1000)}
function vExp(){clearInterval(CT);CT=null;$('#cfx').classList.add('hide');$('#cok').classList.add('hide');$('.lib').classList.add('hide');$('#cexp').classList.remove('hide');lErro()}
function ctick(){if(!ULT)return;const f=Date.parse(ULT.expira_em)-Date.now();if(f<=0){vExp();return}$('#ctm').textContent=String(Math.floor(f/60000)).padStart(2,'0')+':'+String(Math.floor(f%60000/1000)).padStart(2,'0')}
function telaCad(on){const a=on?$('#lf'):$('#cf'),b=on?$('#cf'):$('#lf');a.classList.add('hide');b.classList.remove('hide','sw');void b.offsetWidth;b.classList.add('sw');
 if(on){if(ULT&&!vencida(ULT))vOk();else if(ULT){vExp()}else{vForm();["#cu","#cp","#cp2","#ce"].forEach(x=>{$(x).value=""});$('#cu').focus()}}
 else{limpaErro();$('#lu').focus()}}
$('#cemb').src=$('#lf .emb').src;
$('#addu').onclick=()=>telaCad(true);$('#cback').onclick=()=>telaCad(false);
$('#cnew').onclick=()=>{ultSet(null);vForm();$('#cu').focus()};
$('#clib').addEventListener('input',()=>lErro());
$('#cf').addEventListener('input',e=>{const i=e.target.closest('.in');if(i)i.classList.remove('bad')});
$('#ceye').onclick=()=>{const v=$('#cp').type==='password';['#cp','#cp2'].forEach(x=>$(x).type=v?'text':'password');$('#ceye').innerHTML=ico(v?'eyo':'eye');$('#ceye').setAttribute('aria-label',v?'Ocultar senha':'Mostrar senha');applyI18n($('#cf'))};
function animCad(){return new Promise(res=>{if(!document.getElementById('intro')){document.body.insertAdjacentHTML('beforeend',introHTML());applyI18n($('#intro'));runIntro()}const iv=setInterval(()=>{if(!document.getElementById('intro')){clearInterval(iv);res()}},150);setTimeout(()=>{clearInterval(iv);res()},12000)})}
const ERC={login_invalido:['Login inválido.','Use de 3 a 30 caracteres: letras sem acento, números, ponto, hífen ou sublinhado, sem espaços. Ex.: joao.silva',['#cu']],
 login_indisponivel:['Login indisponível.','Esse login já existe ou já tem um pedido em análise. Escolha outro.',['#cu']],
 email_indisponivel:['E-mail já cadastrado.','Esse e-mail já tem um cadastro. Se foi há mais de 5 minutos sem ativar, aguarde um instante e tente de novo.',['#ce']],
 email_invalido:['E-mail inválido.','Digite um e-mail no formato nome@empresa.com.br.',['#ce']],
 email_nao_autorizado:['E-mail não autorizado.','Use seu e-mail corporativo, terminado em @projeart.ind.br.',['#ce']],
 senha_invalida:['Senha inválida.','A senha precisa ter de 6 a 72 caracteres.',['#cp']],
 muitos_pedidos:['Muitos pedidos.','Muitos cadastros em pouco tempo. Aguarde alguns minutos e tente de novo.',['#cu']],
 email_nao_enviado:['Não foi possível avisar o administrador.','O e-mail para o administrador não pôde ser enviado. Tente de novo em instantes.',['#cu']],
 rede:['Sem conexão com o servidor.','Confira a internet e tente de novo.',['#cu']]};
$('#cf').onsubmit=async e=>{e.preventDefault();cLimpa();
 const l=$('#cu').value.trim().toLowerCase(),s=$('#cp').value,s2=$('#cp2').value,m=$('#ce').value.trim().toLowerCase();
 const vz=[['#cu',!l],['#cp',!s],['#cp2',!s2],['#ce',!m]].filter(x=>x[1]).map(x=>x[0]);
 if(vz.length)return cErro('Preencha todos os campos.','Falta preencher: '+vz.map(x=>CN[x]).join(', ')+'.',vz);
 if(!/^[a-z0-9._-]{3,30}$/.test(l))return cErro(...ERC.login_invalido);
 if(s.length<6)return cErro('Senha muito curta.','A senha precisa ter pelo menos 6 caracteres.',['#cp']);
 if(s!==s2)return cErro('As senhas não conferem.','Digite a mesma senha nos dois campos.',['#cp','#cp2'],'#cp2');
 if(!EMAIL_OK.test(m))return cErro(...ERC.email_invalido);
 if(!/@projeart\.ind\.br$/.test(m))return cErro(...ERC.email_nao_autorizado);
 const b=$('#cfx .btn');b.disabled=true;const r=await chamarRetry('solicitar',{login:l,email:m,senha:s});b.disabled=false;
 if(!r.ok){const x=[...(ERC[r.erro]||['Não foi possível cadastrar.','Tente de novo em instantes.',['#cu']])];if(!ERC[r.erro]||r.erro==='email_nao_enviado')x[1]=TX(x[1])+' ('+(r.detalhe||r.erro||'?')+')';return cErro(...x)}
 ultSet({login:l,email:m,expira_em:r.expira_em});$('#cf').reset();vOk()};
$('#clibb').onclick=async()=>{const k=$('#clib').value.replace(/\s+/g,'');
 if(!/[A-Za-z0-9_-]{32}$/.test(k))return lErro('Chave inválida.','Cole a chave de acesso completa que você recebeu por e-mail.');
 const b=$('#clibb');b.disabled=true;const r=await chamarRetry('ativar',{chave:k});b.disabled=false;
 if(r.erro==='expirada'){ultSet({expira_em:new Date(0).toISOString()});$('#clib').value='';return vExp()}
 if(!r.ok)return r.erro==='rede'?lErro('Sem conexão com o servidor.','Confira a internet e tente de novo.'):lErro('Chave inválida.','Cole a chave de acesso completa que você recebeu por e-mail.');
 ultSet(null);$('#clib').value='';$('.lib').open=false;vForm();telaCad(false);$('#lu').value=r.login;$('#le').value=r.email;$('#lp').value='';$('#lp').focus();
 lOk('Acesso ativado! Digite sua senha e clique em Entrar.')};
/* tela do administrador */
const pend=()=>DB.get('solicitacoes').filter(x=>x.status==='pendente'&&!vencida(x));
const STX={pendente:'Aguardando chave',aprovado:'Ativado',expirado:'Expirado',recusado:'Recusado'};
function usrV(){const P=pend(),U=DB.get('perfis'),R=DB.get('solicitacoes').filter(x=>!(x.status==='pendente'&&!vencida(x))).slice(0,6);
 return`<h2>Usuários e cadastros</h2>
 <div class="pn"><h3>Solicitações pendentes (${P.length})</h3>${P.length?`<div class="tw"><table><tr><th>Login</th><th>E-mail</th><th>Pedido em</th><th>Vale até</th><th>Ação</th></tr>${P.map(x=>`<tr><td>${esc(x.login)}</td><td>${esc(x.email)}</td><td>${hm(x.solicitado_em)}</td><td>${hm(x.expira_em)}</td><td><div class="ua"><button class="mb ok" data-a="apr" data-u="${x.id}">✓ Aprovar agora</button><button class="mb no" data-a="rec" data-u="${x.id}">✕ Recusar</button></div></td></tr>`).join('')}</table></div>`:'<p class="hint" style="margin:0">Nenhum pedido aguardando aprovação.</p>'}
 <p class="hint" style="margin-top:10px">A chave de acesso chega no seu e-mail. Para aprovar, clique em Aprovar agora (mais simples) ou envie a chave ao e-mail corporativo da pessoa em até 5 minutos.</p></div>
 <div class="pn" style="margin-top:12px"><h3>Usuários com acesso (${U.filter(x=>x.ativo).length})</h3><div class="tw"><table><tr><th>Login</th><th>E-mail</th><th>Perfil</th><th>Último acesso</th><th>Situação</th><th>Ação</th></tr>
 ${U.map(x=>`<tr><td>${esc(x.login)}</td><td>${esc(x.email)}</td><td>${esc(x.perfil)}</td><td>${hm(x.ultimo_acesso)}</td><td>${x.admin?'<span class="sit adm">Administrador</span>':!x.ativo&&!x.aprovado_em?'<span class="sit off">Aguardando chave</span>':`<span class="sit ${x.ativo?'on':'off'}">${x.ativo?'Ativo':'Bloqueado'}</span>`}</td><td>${x.admin||(!x.ativo&&!x.aprovado_em)?'—':`<div class="ua"><button class="mb ${x.ativo?'no':'ok'}" data-a="blq" data-u="${x.id}">${x.ativo?'Bloquear':'Desbloquear'}</button></div>`}</td></tr>`).join('')}</table></div></div>
 ${R.length?`<div class="pn" style="margin-top:12px"><h3>Pedidos recentes</h3><div class="tw"><table><tr><th>Login</th><th>E-mail</th><th>Pedido em</th><th>Situação</th></tr>${R.map(x=>`<tr><td>${esc(x.login)}</td><td>${esc(x.email)}</td><td>${hm(x.solicitado_em)}</td><td>${STX[x.status]||x.status}</td></tr>`).join('')}</table></div></div>`:''}`}
async function usrAcao(k,id){if(!(USER&&USER.adm))return;
 if(k==='apr'){const r0=DB.get('solicitacoes').find(x=>x.id===id);if(!r0)return;let tok=null;try{tok=(await SB.auth.getSession()).data.session.access_token}catch(e){}
  const r=await chamarRetry('aprovar',{id},tok);if(!r.ok){await DB.refresh();render();return toast(r.erro==='expirada'?'Esse pedido já expirou: a pessoa precisa refazer o cadastro.':'Não foi possível aprovar agora. Tente de novo.')}
  DB.log('solicitacoes',id,'aprovar',{login:r.login});await DB.refresh();render();return toast(r.login+' aprovado(a). Avise a pessoa: ela já pode entrar com login, e-mail e senha.')}
 if(k==='rec'){const r=DB.get('solicitacoes').find(x=>x.id===id);if(!r)return;if(!confirmT(`Recusar o cadastro de ${r.login}?`))return;
  const {error}=await SB.from('solicitacoes').update({expira_em:DB.now(),analisado_por:USER.id}).eq('id',id);if(error)return falha(error);
  DB.log('solicitacoes',id,'recusar',{login:r.login});await DB.refresh();toast('Cadastro recusado');return render()}
 if(k==='blq'){const u=DB.get('perfis').find(x=>x.id===id);if(!u||u.admin)return;
  const {error}=await SB.from('perfis').update({ativo:!u.ativo}).eq('id',id);if(error)return falha(error);
  DB.log('perfis',id,u.ativo?'bloquear':'desbloquear',{login:u.login});await DB.refresh();toast(u.login+(u.ativo?' bloqueado(a)':' desbloqueado(a)'));render()}}

/* LOGIN */
$('#eye').onclick=()=>{const p=$('#lp'),v=p.type==='password';p.type=v?'text':'password';$('#eye').innerHTML=ico(v?'eyo':'eye');$('#eye').setAttribute('aria-label',v?'Ocultar senha':'Mostrar senha');applyI18n($('#lf'))};
$('#lf').onsubmit=async e=>{e.preventDefault();const l=$('#lu').value.trim().replace(/\s+/g,' ').toLowerCase(),s=$('#lp').value,m=$('#le').value.trim().toLowerCase();
 const vazio=[['#lu',!l],['#lp',!s],['#le',!m]].filter(x=>x[1]).map(x=>x[0]);
 if(vazio.length)return loginErro('Preencha todos os campos.','Falta preencher: '+vazio.map(x=>({'#lu':'login','#lp':'senha','#le':'e-mail'})[x]).join(', ')+'.',vazio);
 if(!/^[^\s@]+@[^\s@]+\.[^\s@]+$/.test(m))return loginErro('E-mail inválido.','Digite um e-mail no formato nome@empresa.com.br.',['#le']);
 if(!SB)return loginErro('Sem conexão com o servidor.','Não foi possível iniciar a conexão. Atualize a página.',['#lu']);
 const bt=$('#lf .btn');if(bt)bt.disabled=true;
 const bad=()=>{FAL++;$('#lp').value='';loginErro('Erro no login.','Login, senha ou e-mail incorretos. Confira os dados e tente de novo.'+(FAL>1?' Tentativa '+FAL+'.':''),['#lu','#lp','#le'],'#lp')};
 try{const {data,error}=await SB.auth.signInWithPassword({email:m,password:s});
  if(error){if(/fetch|network|failed/i.test(error.message||''))return loginErro('Sem conexão com o servidor.','Confira a internet e tente de novo.',['#lu']);return bad()}
  const p=await perfilDe(data.user.id);
  if(!p||p.login!==l){await SB.auth.signOut();return bad()}
  if(!p.ativo){await SB.auth.signOut();return p.aprovado_em?loginErro('Acesso bloqueado.','Seu usuário está bloqueado. Fale com o administrador do sistema.',['#lu'],'#lu'):loginErro('Acesso ainda não ativado.','Use a chave de acesso enviada pelo administrador (CADASTRE-SE › Ativar acesso). Se já passaram 5 minutos, refaça o cadastro.',['#lu'],'#lu')}
  FAL=0;limpaErro();
  try{if($('#lr').checked)localStorage.setItem(RK,JSON.stringify({l:$('#lu').value.trim(),s,e:$('#le').value.trim()}));else localStorage.removeItem(RK)}catch(x){}
  coverIntro();await enter(uObj(p),true)}
 catch(x){console.error(x);const iv0=document.getElementById('intro');if(iv0&&!USER)iv0.remove();loginErro('Sem conexão com o servidor.','Confira a internet e tente de novo.',['#lu'])}
 finally{if(bt)bt.disabled=false}};
function coverIntro(){if(!document.getElementById('intro')){document.body.insertAdjacentHTML('beforeend',introHTML());applyI18n($('#intro'))}}
async function perfilDe(id){const r=await SB.from('perfis').select('*').eq('id',id).maybeSingle();return r.data}
const RK='projeart_pcp:lembrar';let FAL=0;
function lOk(t){const e=$('#lok');e.textContent=t?TX(t):'';e.classList.toggle('hide',!t)}
function limpaErro(){lOk();$('#er').innerHTML='';document.querySelectorAll('#lf .in').forEach(x=>x.classList.remove('bad'))}
function loginErro(t,m,campos,foco){limpaErro();t=TX(t);m=TX(m);$('#er').innerHTML=ico('warn')+'<span><b>'+t+'</b>'+m+'</span>';
 campos.forEach(c=>$(c).closest('.in').classList.add('bad'));const c=$('#lf');c.classList.remove('shk');void c.offsetWidth;c.classList.add('shk');$(foco||campos[0]).focus()}
$('#lf').addEventListener('input',e=>{const i=e.target.closest('.in');if(i)i.classList.remove('bad')});
function fillRemember(){try{const r=JSON.parse(localStorage.getItem(RK));if(r){$('#lu').value=r.l||'';$('#lp').value=r.s||'';$('#le').value=r.e||'';$('#lr').checked=true;return true}}catch(e){}return false}
fillRemember();
$('#lr').onchange=()=>{if(!$('#lr').checked)try{localStorage.removeItem(RK)}catch(e){}};
let POLL=null;
async function enter(u,doLogin){USER=u;await DB.refresh();$('nav .n[data-v=usr]').classList.toggle('hide',!u.adm);SB.rpc('registrar_acesso').then(()=>{},()=>{});DB.log('perfis',u.id,'login');
 $('#login').classList.add('hide');$('#app').classList.remove('hide');setUserLabel();const tl=await loadPrefs();if(doLogin&&ANIM){INTRO=true;go('home')}else{const c0=document.getElementById('intro');if(c0&&doLogin)c0.remove();go(tl)}
 clearInterval(POLL);POLL=setInterval(async()=>{if(!USER||document.hidden)return;const a=document.activeElement,dl=$('#dg');if(dl&&dl.open)return;const ok=await DB.refresh();if(ok&&!(a&&/INPUT|SELECT|TEXTAREA/.test(a.tagName))&&!INTRO&&!document.getElementById('intro'))render()},20000)}
$('#out').onclick=async()=>{clearInterval(POLL);DB.log('perfis',USER&&USER.id,'logout');const s=SB&&SB.auth.signOut();$('#app').classList.add('hide');$('#login').classList.remove('hide');USER=null;ops=[];$('#lp').value='';limpaErro();fillRemember();try{await s}catch(e){}};
function setUserLabel(){if(!USER)return;$('#us').innerHTML=esc(USER.n)+'<small class="us-r"> · '+esc(TX(USER.r))+'</small>'}
function clock(){const d=new Date();$('#dt').textContent=d.toLocaleDateString(LOC[LANG]);$('#hr').textContent=d.toLocaleTimeString(LOC[LANG],{hour:'2-digit',minute:'2-digit'})}clock();setInterval(clock,15000);

/* ÍCONES INDUSTRIAIS (traço) */
const IC={"dash": "<rect x=\"3\" y=\"3\" width=\"7\" height=\"9\" rx=\"1\"/><rect x=\"14\" y=\"3\" width=\"7\" height=\"5\" rx=\"1\"/><rect x=\"14\" y=\"12\" width=\"7\" height=\"9\" rx=\"1\"/><rect x=\"3\" y=\"16\" width=\"7\" height=\"5\" rx=\"1\"/>", "fab": "<path d=\"M2 21h20\"/><path d=\"M3 21V10l5 3v-3l5 3v-3l5 3V4h3v17\"/><path d=\"M7 17h2M11.5 17h2M16 17h2\"/>", "op": "<rect x=\"5\" y=\"4\" width=\"14\" height=\"17\" rx=\"2\"/><path d=\"M9 4V2.8h6V4\"/><path d=\"M9 10h6M9 14h6M9 18h3.5\"/>", "pal": "<rect x=\"4\" y=\"11\" width=\"7\" height=\"6\"/><rect x=\"13\" y=\"11\" width=\"7\" height=\"6\"/><rect x=\"8.5\" y=\"5\" width=\"7\" height=\"6\"/><path d=\"M2 17h20M4 17v3M12 17v3M20 17v3\"/>", "gan": "<path d=\"M3 3v18h18\"/><rect x=\"6\" y=\"5.5\" width=\"7\" height=\"3\" rx=\".6\"/><rect x=\"10\" y=\"10.5\" width=\"8\" height=\"3\" rx=\".6\"/><rect x=\"7\" y=\"15.5\" width=\"6\" height=\"3\" rx=\".6\"/>", "gau": "<path d=\"M3.5 18a9 9 0 1 1 17 0\"/><path d=\"M12 14l4.2-5\"/><circle cx=\"12\" cy=\"14\" r=\"1.6\"/><path d=\"M6.2 11.6l1.2.7M12 6.4v1.4M17.8 11.6l-1.2.7\"/>", "nut": "<path d=\"M12 2.5l8.2 4.75v9.5L12 21.5l-8.2-4.75v-9.5z\"/><path d=\"M8.6 12.3l2.4 2.4 4.5-5\"/>", "kpi": "<path d=\"M3 3v18h18\"/><path d=\"M7 15l4-4 3 3 6-7\"/><path d=\"M16 7h4v4\"/>", "rel": "<path d=\"M14 3H6a1 1 0 0 0-1 1v16a1 1 0 0 0 1 1h12a1 1 0 0 0 1-1V8z\"/><path d=\"M14 3v5h5\"/><path d=\"M9 17v-3M12 17v-6M15 17v-4\"/>", "cfg": "<path d=\"M14.7 6.3a1 1 0 0 0 0 1.4l1.6 1.6a1 1 0 0 0 1.4 0l3.77-3.77a6 6 0 0 1-7.94 7.94l-6.91 6.91a2.12 2.12 0 0 1-3-3l6.91-6.91a6 6 0 0 1 7.94-7.94l-3.76 3.76z\"/>", "cal": "<rect x=\"3\" y=\"5\" width=\"18\" height=\"16\" rx=\"2\"/><path d=\"M3 10h18M8 3v4M16 3v4\"/>", "rel2": "<circle cx=\"12\" cy=\"12\" r=\"9\"/><path d=\"M12 7v5l3 2\"/>", "cap": "<path d=\"M2 17.5h20\"/><path d=\"M4 17.5a8 8 0 0 1 16 0\"/><path d=\"M10 9.6V6h4v3.6\"/><path d=\"M7.5 17.5V14M16.5 17.5V14\"/>", "eye": "<path d=\"M2 12s3.5-7 10-7 10 7 10 7-3.5 7-10 7S2 12 2 12z\"/><circle cx=\"12\" cy=\"12\" r=\"3\"/>", "eyo": "<path d=\"M2 12s3.5-7 10-7 10 7 10 7-3.5 7-10 7S2 12 2 12z\"/><circle cx=\"12\" cy=\"12\" r=\"3\"/><path d=\"M3 3l18 18\"/>", "lock": "<rect x=\"5\" y=\"11\" width=\"14\" height=\"10\" rx=\"2\"/><path d=\"M8 11V7a4 4 0 0 1 8 0v4\"/><path d=\"M12 15v2\"/>", "menu": "<path d=\"M4 6h16M4 12h16M4 18h16\"/>", "warn": "<path d=\"M12 3l10 18H2z\"/><path d=\"M12 10v5M12 18h.01\"/>", "cone": "<path d=\"M9.5 4h5l5 15h-15z\"/><path d=\"M7.7 10h8.6M6.1 15h11.8\"/><path d=\"M3 21h18\"/>"};
IC.db='<ellipse cx="12" cy="5.5" rx="7.5" ry="3"/><path d="M4.5 5.5v6.5c0 1.7 3.4 3 7.5 3s7.5-1.3 7.5-3V5.5"/><path d="M4.5 12v6.5c0 1.7 3.4 3 7.5 3s7.5-1.3 7.5-3V12"/>';IC.moon='<path d="M20 14.5A8 8 0 1 1 9.5 4a6.5 6.5 0 0 0 10.5 10.5z"/>';IC.sun='<circle cx="12" cy="12" r="4"/><path d="M12 2v2M12 20v2M4.9 4.9l1.4 1.4M17.7 17.7l1.4 1.4M2 12h2M20 12h2M4.9 19.1l1.4-1.4M17.7 6.3l1.4-1.4"/>';
IC.usr='<circle cx="10.5" cy="8" r="4.2"/><path d="M3.5 20.5a7.5 7.5 0 0 1 12.2-5.8"/><path d="M18.5 15v6M15.5 18h6"/>';
const ico=(n,c='')=>`<svg class="ic ${c}" viewBox="0 0 24 24" aria-hidden="true">${IC[n]}</svg>`;

/* NAV */
const NAV=[['home','Tela inicial','dash'],['prod','Produção','fab'],['val','Processo de validação','op'],['ops','Ordens de Produção','op'],['rot','Gerenciador de Roteiros','pal'],['exp','Área de impressão','fab'],['plan','Planejamento','gan'],['cap','Capacidade','gau'],['qual','Qualidade / RNC','nut'],['kpi','Indicadores','kpi'],['rel','Relatórios','rel'],['usr','Usuários','usr'],['cfg','Configurações','cfg']];
const CHV='<svg class="ic chv" viewBox="0 0 24 24" aria-hidden="true"><path d="M6 9l6 6 6-6"/></svg>';
const GRP={val:['pg8'],rot:['pg10','pg11'],exp:['pg12']};const grpOf=id=>GRP.val.includes(id)?'val':GRP.rot.includes(id)?'rot':GRP.exp.includes(id)?'exp':'prod';
const subHTML=k=>`<div class="sub" id="sub-${k}">${PROG.filter(p=>grpOf(p[0])===k).map(p=>`<button class="n" data-v="${p[0]}">${ico('rel')}<span>${p[1]}</span></button>`).join('')}</div>`;
$('#nv').innerHTML=NAV.map(n=>n[0]==='ops'?'':(n[0]==='prod'||n[0]==='val'||n[0]==='rot'||n[0]==='exp')?`<button class="n grp" data-tg="${n[0]}" aria-expanded="false">${ico(n[2])}<span>${n[1]}</span>${CHV}</button>${subHTML(n[0])}`:`<button class="n" data-v="${n[0]}">${ico(n[2])}<span>${n[1]}</span></button>`).join('')+'<div class="plant"><img src="'+$('#nv').dataset.plant+'" alt="" decoding="async"><div><b>Grupo Projeart</b><br>Indústria Metalúrgica</div></div>';
$('#nv').onclick=e=>{const t=e.target.closest('[data-tg]');if(t){const k=t.dataset.tg;return subTg(!$('#sub-'+k).classList.contains('open'),k)}const b=e.target.closest('[data-v]');if(b)go(b.dataset.v)};$('#bg').onclick=()=>$('#nv').classList.toggle('open');

/* V72 · estado da conexão: online / congestionamento / buffer */
let NET='ok';const NETTXT={ok:'Sistema online',slow:'Sistema Congestionamento',buf:'Sistema Buffer'};
const NETLOG=[];let netFalhas=0;
function netUI(){document.querySelectorAll('main .onl').forEach(e=>{e.className='onl'+(NET==='ok'?'':' '+NET);e.lastChild.textContent=NETTXT[NET]});
 document.querySelectorAll('.st span').forEach(e=>{const i=e.querySelector('i'),t=e.lastChild;if(!i||!t)return;i.style.background=NET==='ok'?'':NET==='slow'?'#e0a21a':'#ef4444';t.textContent=' '+NETTXT[NET]+(' · dados salvos no servidor · '+VERSAO)})}
function netSet(n){if(n!==NET){NET=n;netUI()}}
async function netMedir(){
 if(navigator.onLine===false){netFalhas=3;return netSet('buf')}
 const t0=performance.now(),ac=new AbortController(),to=setTimeout(()=>ac.abort(),8000);
 try{await fetch(SB_URL+'/auth/v1/health',{mode:'no-cors',cache:'no-store',signal:ac.signal});netFalhas=0;NETLOG.push(performance.now()-t0)}
 catch(e){netFalhas++;NETLOG.push(8000)}
 clearTimeout(to);if(NETLOG.length>3)NETLOG.shift();
 const med=[...NETLOG].sort((a,b)=>a-b)[Math.floor(NETLOG.length/2)];
 netSet(netFalhas>=2||med>=6000?'buf':(netFalhas===1||med>=1200)?'slow':'ok')}
window.addEventListener('offline',()=>{netFalhas=3;netSet('buf')});window.addEventListener('online',()=>netMedir());
setInterval(netMedir,6000);setTimeout(netMedir,1500);
window.__net=n=>{netSet(n)};window.__irEnvioRoteiro=()=>go('pg11');
/* ===== ATUALIZAÇÃO AUTOMÁTICA (publicado na web) =====
   Compara a versão deste sistema com /versao.json do servidor. Se houver uma nova, avisa o usuário (ou atualiza sozinho na tela de login). */
(function(){
  if(!/^https?:$/.test(location.protocol))return;
  const ATUAL=VERSAO;let avisada='',ocupado=false;
  function banner(nova){
    if(document.getElementById('updAviso'))return;
    const d=document.createElement('div');d.id='updAviso';d.setAttribute('role','status');
    d.style.cssText='position:fixed;right:18px;top:18px;z-index:99999;display:flex;align-items:center;gap:12px;background:#e8ebef;color:#1f2937;border:1px solid #c9d0d9;border-left:5px solid #0b5cad;border-radius:10px;padding:12px 14px;box-shadow:0 8px 28px rgba(0,0,0,.35);font:600 13px "Segoe UI",Inter,system-ui,sans-serif;max-width:420px';
    d.innerHTML='<span><b style="font-weight:800">Nova versão disponível</b><br><span style="font-weight:500;color:#4b5563">'+nova+' — salve o que estiver fazendo e atualize.</span></span>'
      +'<button id="updOk" style="background:#0b5cad;color:#fff;border:1px solid #0b5cad;border-radius:7px;padding:8px 14px;font:700 13px inherit;cursor:pointer">Atualizar agora</button>'
      +'<button id="updNo" aria-label="Depois" style="background:#f2f4f6;color:#1f2937;border:1px solid #c5cbd6;border-radius:7px;padding:8px 10px;font:700 13px inherit;cursor:pointer">Depois</button>';
    document.body.appendChild(d);
    d.querySelector('#updOk').onclick=()=>location.reload();
    d.querySelector('#updNo').onclick=()=>d.remove();
  }
  async function checar(){
    if(ocupado||document.hidden)return;ocupado=true;
    try{
      const r=await fetch('versao.json?t='+Date.now(),{cache:'no-store'});
      if(!r.ok)return;const j=await r.json();
      if(j&&j.versao&&j.versao!==ATUAL&&j.versao!==avisada){
        avisada=j.versao;banner(j.versao);
      }
    }catch(e){}finally{ocupado=false}
  }
  /* depois que a versão nova abre (pelo botão ou F5): avisa que o sistema foi atualizado */
  (function(){let antes='';try{antes=localStorage.getItem('projeart_pcp:versao')||'';localStorage.setItem('projeart_pcp:versao',ATUAL)}catch(e){return}
    if(!antes||antes===ATUAL)return;
    const mostra=()=>{if(document.getElementById('updFeito'))return;const d=document.createElement('div');d.id='updFeito';d.setAttribute('role','status');
      d.style.cssText='position:fixed;right:18px;top:18px;z-index:99999;display:flex;align-items:center;gap:12px;background:#e8ebef;color:#1f2937;border:1px solid #c9d0d9;border-left:5px solid #16a34a;border-radius:10px;padding:12px 14px;box-shadow:0 8px 28px rgba(0,0,0,.35);font:600 13px Arial,Helvetica,sans-serif;max-width:420px';
      d.innerHTML='<span><b style="font-weight:800">Sistema atualizado</b><br><span style="font-weight:500;color:#4b5563">'+antes+' → '+ATUAL+'. Você já está na versão nova.</span></span><button id="updFeitoOk" style="background:#0b5cad;color:#fff;border:1px solid #0b5cad;border-radius:7px;padding:8px 14px;font:700 13px Arial,Helvetica,sans-serif;cursor:pointer">OK</button>';
      document.body.appendChild(d);d.querySelector('#updFeitoOk').onclick=()=>d.remove();setTimeout(()=>{if(d.isConnected)d.remove()},12000)};
    if(document.body)setTimeout(mostra,1200);else document.addEventListener('DOMContentLoaded',()=>setTimeout(mostra,1200))})();
  setInterval(checar,90000);
  document.addEventListener('visibilitychange',()=>{if(!document.hidden)checar()});
  window.addEventListener('focus',checar);
  setTimeout(checar,5000);
})();

let cur='home';const F={p:'',s:'',q:''};let CM=new Date();CM.setDate(1);
function subTg(o,k){k=k||'prod';$('#sub-'+k).classList.toggle('open',o);const g=$('nav .grp[data-tg='+k+']');g.setAttribute('aria-expanded',o);g.classList.toggle('opn',o)}
function go(v){cur=v;$('#nv').classList.remove('open');document.querySelectorAll('nav .n').forEach(b=>b.classList.toggle('on',b.dataset.v===v));{const gv=/^pg/.test(v)?grpOf(v):'';['prod','val','rot','exp'].forEach(k=>{if(gv===k)subTg(true,k);$('nav .grp[data-tg='+k+']').classList.toggle('in',gv===k)})}render();scrollTo(0,0);savePrefs()}
function prodV(){const p=PROG.find(x=>x[0]===cur);return`<div class="prh"><h2 class="up"${/^pg(?:[1-9]|1[0-2])$/.test(cur)?' style="text-align:center"':''}>${p[2]}</h2>${/^pg(?:[1-9]|1[0-2])$/.test(cur)?`<span class="onl${NET==='ok'?'':' '+NET}" role="status"><i></i>${NETTXT[NET]}</span>`:''}</div><div class="pn" style="padding:0;overflow:hidden;background:${/^pg(?:[1-9]|1[0-2])$/.test(cur)?'#eef1f6':'#0b0e14'}"><iframe id="ppcp" data-pg="${cur}" title="${p[2]}" style="width:100%;height:calc(100vh - 170px);min-height:520px;border:0;display:block"></iframe></div>`}
function render(){if(cur==='prod')cur='pg3';if(cur==='val')cur='pg8';if(cur==='rot')cur='pg10';if(cur==='exp')cur='pg12';{const f=$('#ppcp');if(/^pg/.test(cur)&&f&&f.dataset.pg===cur)return}if(cur==='usr'&&!(USER&&USER.adm))cur='home';const nb=$('nav .n[data-v=usr]');if(nb){const q=USER&&USER.adm?pend().length:0;nb.innerHTML=ico('usr')+'<span>Usuários</span>'+(q?`<span class="nb" title="Cadastros aguardando aprovação">${q}</span>`:'')}
 const isP=/^pg/.test(cur);const V=isP?prodV:{home,ops:opsV,plan:planV,cfg:cfgV,usr:usrV}[cur];const nm=isP?'':NAV.find(n=>n[0]===cur)[1];
 $('#view').innerHTML=V?V():`<h2>${nm}</h2><div class="pn empty"><b>${ico('cone')}</b>Este módulo chega em uma versão futura.<br>Diga o que ele precisa fazer e montamos o próximo.</div>`;
 $('#view').insertAdjacentHTML('beforeend',`<div class="st"><span><i style="${NET==='ok'?'':NET==='slow'?'background:#e0a21a':'background:#ef4444'}"></i>${NETTXT[NET]} · dados salvos no servidor · ${VERSAO}</span></div>`);{const u=$('#upd');if(u)u.innerHTML=`<span><i class="dt">•</i> Última atualização: <b>${hm(DB.meta().atualizado_em)}</b></span>`}if(/^pg/.test(cur)){const f=$('#ppcp');if(f&&!f.srcdoc)f.srcdoc=document.getElementById('src-'+cur).textContent.replace(/<\\\/script/g,'</script')}if(cur==='ops')lst();if(cur==='home')initPk();applyI18n($('#app'));markUI();if(cur==='home'&&INTRO){INTRO=false;coverIntro();runIntro()}}
const filt=()=>`<div class="tb"><select id="xp" aria-label="Processo"><option value="">Todos os processos</option>${[['Corte','OF - Obra'],['Solda','N° Lote']].map(p=>`<option value="${p[0]}" ${F.p===p[0]?'selected':''}>${p[1]}</option>`).join('')}</select><select id="xs" aria-label="Status"><option value="">Status</option>${[['Em aberto','PCT - Impresso'],['Em produção','PCT - Não Impresso'],['Concluída','Concluído'],['Dobra','Sub - trecho']].map(p=>`<option value="${p[0]}" ${F.s===p[0]?'selected':''}>${p[1]}</option>`).join('')}</select>`;
$('#view').addEventListener('change',e=>{if(e.target.id==='anim'&&USER&&USER.adm){ANIM=e.target.checked;savePrefs();toast(ANIM?'Animação de abertura ligada':'Animação de abertura desligada')}if(e.target.id==='xp'){F.p=e.target.value;render();savePrefs()}if(e.target.id==='xs'){F.s=e.target.value;render();savePrefs()}});
$('#view').addEventListener('input',e=>{if(e.target.id==='xq'){F.q=e.target.value;lst();clearTimeout(window._pq);window._pq=setTimeout(savePrefs,500)}});
$('#view').addEventListener('click',e=>{const r=e.target.closest('[data-id]');if(r)return openOP(r.dataset.id);const a=e.target.closest('[data-a]');if(!a)return;const k=a.dataset.a;
 if(k==='new')openOP();if(k==='pm'||k==='nm'){CM.setMonth(CM.getMonth()+(k==='nm'?1:-1));render();savePrefs()}if(k==='exp')exportar();if(k==='seedb')semear();if(['rec','blq','apr'].includes(k))usrAcao(k,a.dataset.u);if(k==='intro'){INTRO=true;go('home')}});
const L=()=>ops.filter(o=>(!F.p||o.proc===F.p)&&(!F.s||(F.s==='Dobra'?o.proc==='Dobra':stat(o)===F.s)));
const trs=(a,late)=>a.length?a.sort((x,y)=>x.prazo<y.prazo?-1:1).map(o=>`<tr data-id="${o.id}"><td>${o.id}</td><td>${esc(o.produto)}</td><td>${nf(o.qtde)}</td><td>${o.proc}</td><td>${fd(o.prazo)}</td><td>${late?Math.max(0,Math.round((new Date(today())-new Date(o.prazo))/864e5))+' d':nf(o.feito)}</td><td>${bd(o)}</td></tr>`).join(''):`<tr><td colspan="7" style="text-align:center;color:var(--mu)">Nenhuma OP nesta lista.</td></tr>`;
const tbl=(a,h,late)=>`<div class="tw"><table><tr><th>OP</th><th>Produto</th><th>Qtde</th><th>Processo</th><th>Prazo</th><th>${h}</th><th>Status</th></tr>${trs(a,late)}</table></div>`;


/* PACOTES / OBRAS — cada OP é uma obra; o pacote vem do campo pacote da OP (se existir) ou do pacote atual */
const pkOf=o=>String(o.pacote||PACOTE_ATUAL);
function pkList(){const m={};ops.forEach(o=>{const k=pkOf(o);(m[k]=m[k]||{k,n:0,c:0}).n++;if(o.st==='Concluída')m[k].c++});return Object.values(m).sort((a,b)=>(+b.k||0)-(+a.k||0)).map(x=>({...x,p:Math.round(x.c/x.n*100)}))}
const obSt=o=>{const s=stat(o);return s==='Concluída'?['Impressa','c-imp','#1d8a4a',3]:s==='Em produção'?['Em produção','c-pro','#0b5cad',2]:s==='Atrasada'?['Atrasada','c-atr','#d92d2d',2]:['Pendente','c-pen','#d48a1a',1]};
function pkHTML(){const L=pkList();if(!L.length)return'<div class="pvz">Nenhum pacote ainda.</div>';const mx=Math.max(...L.map(x=>x.n),1);
 return L.map(p=>`<button class="prw ppac" data-pac="${esc(p.k)}"><span><b>Pacote ${esc(p.k)}</b></span><span class="pmini"><span class="ptr"><i style="width:${p.n/mx*100}%;background:#7a8fa6"></i></span>${p.n}</span><span class="ptr"><i style="width:${p.p}%;background:${p.p===100?'#1d8a4a':'#0b5cad'}"></i></span><span class="ppct">${p.p}%</span></button>`).join('')}
function obHTML(){if(!ops.length)return'<div class="pvz">Nenhuma obra nesta lista.</div>';
 return ops.slice().sort((a,b)=>((+pkOf(b)||0)-(+pkOf(a)||0))||(a.id<b.id?-1:1)).map(o=>{const t=obSt(o);return`<button class="prw pobr" data-obra="${esc(o.id)}" data-pac="${esc(pkOf(o))}"><span class="pcode">${esc(o.id)}</span><span class="psub">${esc(o.sub_trecho||o.subtrecho||'—')}</span><span>Pacote ${esc(pkOf(o))}</span><span class="pchip ${t[1]}">${t[0]}</span></button>`}).join('')}
function initPk(){const V=$('#view'),listP=$('#listP',V),listO=$('#listO',V),info=$('#pinfo',V);if(!listP||!listO)return;
 const reduce=matchMedia('(prefers-reduced-motion: reduce)').matches,TXT0='Clique em uma obra: as duas listas rolam até ela e o pacote dela fica marcado.',boxP=$('#boxP',V),boxO=$('#boxO',V),bars=new Map(),anims=new WeakMap();
 function setup(box){const list=box.querySelector('.plist'),track=box.querySelector('.ptrack'),thumb=box.querySelector('.pthumb');
  function sync(){const H=track.clientHeight,ratio=list.scrollHeight?list.clientHeight/list.scrollHeight:1;track.style.display=ratio>=1?'none':'';const th=Math.max(28,H*ratio);thumb.style.height=th+'px';const max=list.scrollHeight-list.clientHeight;thumb.style.top=(max>0?list.scrollTop/max*(H-th):0)+'px'}
  list.addEventListener('scroll',sync);if(window.ResizeObserver)new ResizeObserver(sync).observe(list);
  let drag=null;thumb.addEventListener('pointerdown',e=>{e.preventDefault();drag={y:e.clientY,top:list.scrollTop};thumb.setPointerCapture(e.pointerId);box.classList.add('moving');thumb.style.cursor='grabbing'});
  thumb.addEventListener('pointermove',e=>{if(!drag)return;const H=track.clientHeight-thumb.offsetHeight,max=list.scrollHeight-list.clientHeight;list.scrollTop=drag.top+(e.clientY-drag.y)/H*max});
  thumb.addEventListener('pointerup',()=>{drag=null;box.classList.remove('moving');thumb.style.cursor=''});
  track.addEventListener('click',e=>{if(e.target!==track)return;const r=track.getBoundingClientRect();animateTo(box,(e.clientY-r.top)/r.height*(list.scrollHeight-list.clientHeight))});
  sync();bars.set(box,{list,track,sync})}
 function animateTo(box,target){const {list}=bars.get(box);target=Math.max(0,Math.min(target,list.scrollHeight-list.clientHeight));if(reduce){list.scrollTop=target;return}
  cancelAnimationFrame(anims.get(box));const from=list.scrollTop,d=target-from,dur=Math.min(900,350+Math.abs(d)*.6),t0=performance.now();box.classList.add('moving');const ease=t=>t<.5?4*t*t*t:1-Math.pow(-2*t+2,3)/2;
  (function step(now){const t=Math.min(1,(now-t0)/dur);list.scrollTop=from+d*ease(t);if(t<1)anims.set(box,requestAnimationFrame(step));else setTimeout(()=>box.classList.remove('moving'),350)})(t0)}
 function centerOn(box,el){const {list}=bars.get(box),h=list.querySelector('.pth');const head=h?h.offsetHeight:0;animateTo(box,el.offsetTop-head-(list.clientHeight-head)/2+el.offsetHeight/2)}
 function markOn(box,els){const {list,track}=bars.get(box);track.querySelectorAll('.pmark').forEach(m=>m.remove());els.forEach(el=>{const m=document.createElement('span');m.className='pmark ping';m.style.top=(el.offsetTop/list.scrollHeight*track.clientHeight)+'px';track.appendChild(m)})}
 const flash=el=>{el.classList.remove('flash');void el.offsetWidth;el.classList.add('flash')},clearSel=()=>V.querySelectorAll('.prw.sel,.prw.group').forEach(r=>r.classList.remove('sel','group'));
 [boxP,boxO].forEach(setup);
 const pEls=k=>listP.querySelector(`[data-pac="${CSS.escape(k)}"]`),PL=pkList();
 function pickObra(el){const o=ops.find(x=>x.id===el.dataset.obra);if(!o)return;clearSel();el.classList.add('sel');flash(el);const pe=pEls(el.dataset.pac);if(pe){pe.classList.add('sel');flash(pe);centerOn(boxP,pe);markOn(boxP,[pe])}centerOn(boxO,el);markOn(boxO,[el]);const t=obSt(o);info.innerHTML=`<span>Obra <b>${esc(o.id)}</b> · Pacote <b>${esc(pkOf(o))}</b> · <span class="pchip ${t[1]}">${t[0]}</span></span>`}
 function pickPac(el){const k=el.dataset.pac;clearSel();el.classList.add('sel');flash(el);centerOn(boxP,el);markOn(boxP,[el]);const rows=[...listO.querySelectorAll(`.pobr[data-pac="${CSS.escape(k)}"]`)],p=PL.find(x=>x.k===k)||{n:0,p:0};
  if(rows.length){rows.forEach(r=>r.classList.add('group'));centerOn(boxO,rows[0]);markOn(boxO,rows);rows.forEach(flash)}else markOn(boxO,[]);
  info.innerHTML=`<span>Pacote <b>${esc(k)}</b> · ${p.n} ${p.n===1?'obra':'obras'} · ${p.p}% impresso${rows.length?` · ${rows.length} ${rows.length===1?'obra':'obras'} nesta lista`:' · nenhuma obra dele nesta lista'}</span>`}
 listP.addEventListener('click',e=>{const b=e.target.closest('.ppac');if(b)pickPac(b)});listO.addEventListener('click',e=>{const b=e.target.closest('.pobr');if(b)pickObra(b)});
 info.textContent=TXT0}
/* INÍCIO */
function home(){const A=ops.slice(),c=k=>A.filter(o=>stat(o)===k).length,pl=sum(A,'qtde'),rl=sum(A,'feito'),pc=pl?Math.round(rl/pl*100):0,n=A.length||1;
 const kp=(t,v,s,c,x='')=>`<div class="k" style="--c:${c}"><small>${t}</small><div class="v">${v}</div>${x}<small>${s}</small></div>`;
 const q=f=>nf(sum(A.filter(f),'qtde')),pend=nf(sum(A.filter(o=>o.st!=='Concluída'),'qtde')-sum(A.filter(o=>o.st!=='Concluída'),'feito'));
 const kc=`<div class="kg">${kp('Pacote atual',nf(PACOTE_ATUAL),'Pacote listado','#2b8cff')}${kp('% Porcentagem impresso',(A.length?Math.round(c('Concluída')/n*100):0)+'%','em produção agora','#22c55e')}${kp('Total já realizados',nf(rl),pc+'% de '+nf(pl),'#8b5cf6',`<div class="bar" style="--c:#8b5cf6"><i style="width:${Math.min(100,pc)}%"></i></div>`)}${kp('Obras para impressão',`<span style="white-space:nowrap;font-size:.9em">${esc(OBRA_IMPRESSAO)}</span>`,'ainda por produzir','#38bdf8')}${kp('Obras impressas',q(o=>stat(o)==='Atrasada'),'','#ef4444')}${kp('Obras pendente',q(o=>stat(o)==='Em aberto'),'aguardando início','#64748b')}</div>`;
 return`<div class="prh"><h2 class="up" style="text-align:center">Visão geral do dia</h2><span class="onl${NET==='ok'?'':' '+NET}" role="status"><i></i>${NETTXT[NET]}</span></div><div class="hw">${kc}<div class="pcw"><div class="pinfo" id="pinfo" aria-live="polite">Clique em uma obra: as duas listas rolam até ela e o pacote dela fica marcado.</div><section class="pcc"><div class="pch"><h3>Pacote impresso</h3><span class="pcnt">${pkList().length} ${pkList().length===1?'pacote':'pacotes'}</span><span class="phint">clique no pacote para ver as obras dele</span></div><div class="psb" id="boxP"><div class="plist" id="listP"><div class="pth ppac"><span>Pacote</span><span>Obras</span><span>Impressão</span><span style="text-align:right">%</span></div>${pkHTML()}</div><div class="ptrack"><div class="pthumb"></div></div></div></section><section class="pcc"><div class="pch"><h3>Obras</h3><span class="pcnt">${ops.length} ${ops.length===1?'obra':'obras'}</span><span class="phint">clique na obra</span></div><div class="psb" id="boxO"><div class="plist" id="listO"><div class="pth pobr"><span>Obra</span><span>Sub-trecho</span><span>Pacote</span><span>Status</span></div>${obHTML()}</div><div class="ptrack"><div class="pthumb"></div></div></div></section></div></div>`}

/* OPs */
function opsV(){return`<h2>Ordens de Produção</h2>${filt()}<input id="xq" placeholder="Buscar por OP ou produto" value="${esc(F.q)}" aria-label="Buscar"><button class="btn" data-a="new">+ Nova OP</button></div><div class="pn" id="opl"></div>`}
function lst(){const q=F.q.toLowerCase(),a=L().filter(o=>(o.id+o.produto).toLowerCase().includes(q));$('#opl').innerHTML=tbl(a,'Produzido')+`<p style="color:var(--mu);margin-top:8px;font-size:12px">${a.length} OP(s). Toque numa linha para apontar produção ou editar.</p>`;applyI18n($('#opl'))}

/* PLANEJAMENTO */
function planV(){const y=CM.getFullYear(),m=CM.getMonth(),f=new Date(y,m,1).getDay(),dm=new Date(y,m+1,0).getDate(),t=today();let h='';
 for(let i=0;i<f;i++)h+='<div class="cd o"></div>';
 for(let d=1;d<=dm;d++){const k=iso(new Date(y,m,d));h+=`<div class="cd ${k===t?'t':''}"><b>${d}</b>${ops.filter(o=>o.prazo===k).map(o=>`<button class="ch" style="--c:${COL[risk(o)?'Em risco':stat(o)]}" data-id="${o.id}" title="${esc(o.produto)}">${o.id.slice(3)} ${esc(o.produto)}</button>`).join('')}</div>`}
 return`<h2>Planejamento · prazos de entrega</h2><div class="tb"><button class="btn g" data-a="pm" aria-label="Mês anterior">‹</button><b style="align-self:center;min-width:140px;text-align:center">${CM.toLocaleDateString(LOC[LANG],{month:'long',year:'numeric'})}</b><button class="btn g" data-a="nm" aria-label="Próximo mês">›</button><button class="btn" data-a="new">+ Nova OP</button></div><div class="cal">${['Dom','Seg','Ter','Qua','Qui','Sex','Sáb'].map(d=>`<div class="cw">${d}</div>`).join('')}${h}</div>`}

/* CONFIG */
function cfgV(){const m=DB.meta(),ad=USER&&USER.adm,T=ad?{ops:['Ordens de produção',ops.length],apontamentos:['Apontamentos',DB.nAp()],historico:['Ações registradas (últimas)',DB.get('historico').length],perfis:['Usuários',DB.get('perfis').length],solicitacoes:['Solicitações de cadastro',DB.get('solicitacoes').length]}:{ops:['Ordens de produção',ops.length]};
 return`<h2>Configurações</h2><div class="pn"><h3>Banco de dados na nuvem</h3>
 <p style="color:var(--mu);margin-bottom:12px">Tudo o que você cadastra é salvo na hora no servidor privado da empresa (Supabase). Só usuários ativos e autenticados conseguem ver os dados.</p>
 <div class="dbt">${Object.keys(T).map(t=>`<div><b>${nf(T[t][1])}</b><small>${T[t][0]}</small></div>`).join('')}</div>
 <p style="color:var(--mu);font-size:12px;margin-bottom:12px">Última atualização: <b style="color:var(--tx)">${hm(m.atualizado_em)}</b> · Conexão: <b style="color:var(--tx)">${OFF?'sem conexão':'online'}</b></p>
 ${ad?`<div class="tb"><button class="btn g" data-a="exp">Exportar backup (JSON)</button>${ops.length?'':'<button class="btn" data-a="seedb">Carregar OPs de exemplo</button>'}</div>`:''}</div>
 <div class="pn" style="margin-top:12px"><h3>Aparência</h3><div class="ap"><span class="cl">Tema</span><div class="seg" role="group" aria-label="Tema"><button type="button" data-th="dark">${ico('moon')}Escuro</button><button type="button" data-th="light">${ico('sun')}Claro</button></div></div><div class="ap"><span class="cl">Idioma</span><div class="seg" role="group" aria-label="Idioma"><button type="button" data-lg="en">English</button><button type="button" data-lg="es">Español</button><button type="button" data-lg="pt">Português</button></div></div>${ad?`<label class="chk" style="color:var(--tx);margin:4px 0 10px"><input type="checkbox" id="anim" ${ANIM?'checked':''}> Mostrar a animação de abertura ao entrar no sistema <small style="color:var(--mu);font-weight:400">(opção só do administrador)</small></label>`:'<p class="hint" style="margin:4px 0 10px">A animação de abertura é obrigatória ao entrar no sistema.</p>'}<button class="btn g" data-a="intro">▶ Ver animação agora</button></div>
 ${ad?`<div class="pn" style="margin-top:12px"><h3>Últimas ações registradas</h3>${(()=>{const h=DB.get('historico'),nm=id=>(DB.get('perfis').find(p=>p.id===id)||{}).login||'—';return h.length?`<div class="tw"><table><tr><th>Quando</th><th>Usuário</th><th>Ação</th><th>Registro</th></tr>${h.map(x=>`<tr><td>${hm(x.em)}</td><td>${esc(nm(x.usuario))}</td><td>${esc(x.acao)}</td><td>${esc(x.registro_id||'—')}</td></tr>`).join('')}</table></div>`:'<p style="color:var(--mu)">Nenhuma ação registrada ainda.</p>'})()}</div>`:''}
 <div class="pn" style="margin-top:12px"><h3>Sobre o sistema</h3><p style="color:var(--mu);line-height:1.6"><b style="color:var(--tx)">Sistema Operacional · Grupo Projeart</b> · ${VERSAO}<br>Módulos desta versão: Tela inicial, Ordens de Produção, Planejamento, Usuários e Configurações.<br>Previstos para a próxima versão: Produção, Materiais / Estoque, Capacidade, Qualidade / RNC, Indicadores e Relatórios.</p></div>`}
function baixar(txt,tipo,nome){const a=document.createElement('a');a.href=URL.createObjectURL(new Blob([txt],{type:tipo}));a.download=nome;document.body.append(a);a.click();a.remove();setTimeout(()=>URL.revokeObjectURL(a.href),2000)}
function exportar(){baixar(JSON.stringify({sistema:'Sistema Operacional - Grupo Projeart',versao:VERSAO,exportado_em:DB.now(),tabelas:{ops,perfis:DB.get('perfis').map(p=>({login:p.login,email:p.email,perfil:p.perfil,ativo:p.ativo}))}},null,1),'application/json','projeart-pcp-backup-'+today()+'.json');DB.log('sistema',null,'exportar_json');toast('Backup exportado')}
async function semear(){if(!(USER&&USER.adm)||ops.length)return;const {error}=await SB.from('ops').insert(seed());if(error)return falha(error);DB.log('ops',null,'carregar_exemplo');await DB.refresh();toast('Dados de exemplo carregados');render()}


/* APONTAMENTO GIRATÓRIO · CometDial portado para JS puro (mola, arrasto, inércia e rastro) */
const Dial=(()=>{
 const R=80,DEAD=44,K=12,V_FULL=4,V_FLICK=2,TAU=2*Math.PI,TICK=TAU/K,NS='http://www.w3.org/2000/svg',N=10;
 const rm=matchMedia('(prefers-reduced-motion: reduce)'),sv=$('#cdsvg'),wr=$('#cdw'),hd=$('#cdh'),hl=$('#cdhl'),pg=$('#cdp'),vv=$('#cdv'),vs=$('#cdsub'),ff=$('#ff'),fq=$('#fq');
 const PC=TAU*66;pg.style.strokeDasharray=PC;
 const segs=[...Array(N)].map(()=>{const p=document.createElementNS(NS,'path');$('#cdt').append(p);return p});
 for(let i=0;i<K;i++){const a=i*TICK-Math.PI/2,l=document.createElementNS(NS,'line');l.setAttribute('x1',76*Math.cos(a));l.setAttribute('y1',76*Math.sin(a));l.setAttribute('x2',84*Math.cos(a));l.setAttribute('y2',84*Math.sin(a));$('#cdk').append(l)}
 let ang=-Math.PI/2,acc=0,v=0,max=0,base=0,step=1,mode=0,last=null,lt=0,om=0,tgt=ang,sp=0,hist=[],raf=0,ft=0;
 const P=a=>(R*Math.cos(a)).toFixed(2)+' '+(R*Math.sin(a)).toFixed(2);
 const arc=(a0,a1)=>{const s=a1-a0;return`M${P(a0)}A${R} ${R} 0 ${Math.abs(s)>Math.PI?1:0} ${s>0?1:0} ${P(a1)}`};
 function draw(){const x=R*Math.cos(ang),y=R*Math.sin(ang);for(const c of[hd,hl]){c.setAttribute('cx',x);c.setAttribute('cy',y)}
  const now=performance.now();hist=hist.filter(h=>now-h.t<240);
  if(!rm.matches&&hist.length){const span=Math.max(-5,Math.min(5,ang-hist[0].a)),a0=ang-span;
   segs.forEach((p,i)=>{p.setAttribute('d',Math.abs(span)>.01?arc(a0+span*i/N,a0+span*(i+1)/N):'');p.style.opacity=((i+1)/N)**1.6;p.style.strokeWidth=2+8*(i+1)/N})}
  else segs.forEach(p=>p.setAttribute('d',''));
  const r=max?v/max:0;pg.style.strokeDashoffset=PC*(1-r);pg.style.stroke=r>=1?'var(--gr)':'var(--bl)';
  vv.textContent=nf(v);const d=v-base;vs.textContent=max?Tf(`de ${nf(max)} · ${d>=0?'+':''}${nf(d)} agora`,`of ${nf(max)} · ${d>=0?'+':''}${nf(d)} now`,`de ${nf(max)} · ${d>=0?'+':''}${nf(d)} ahora`):Tf('informe a quantidade','enter the quantity','indica la cantidad');
  wr.classList.toggle('off',!max);sv.setAttribute('aria-valuenow',v);sv.setAttribute('aria-valuemax',max);sv.setAttribute('aria-valuetext',Tf(`${nf(v)} de ${nf(max)} peças`,`${nf(v)} of ${nf(max)} pieces`,`${nf(v)} de ${nf(max)} piezas`))}
 function bump(n){const nv=Math.max(0,Math.min(max,v+n));if(nv===v)return false;v=nv;ff.value=v;if(navigator.vibrate&&!rm.matches)try{navigator.vibrate(4)}catch(e){}return true}
 function turn(d,speed){const blocked=(d>0&&v>=max)||(d<0&&v<=0);
  if(blocked){if(Math.abs(acc+d*.2)<TICK*.8){ang+=d*.2;acc+=d*.2}if(mode===2)om=0;hist.push({a:ang,t:performance.now()});return}
  ang+=d;acc+=d;hist.push({a:ang,t:performance.now()});const m=speed>V_FULL?10:1;
  while(acc>=TICK){acc-=TICK;if(!bump(step*m)){acc+=TICK;break}}while(acc<=-TICK){acc+=TICK;if(!bump(-step*m)){acc-=TICK;break}}}
 function settle(){tgt=ang-acc;acc=0;sp=0;if(rm.matches){ang=tgt;mode=0;draw()}else mode=3;loop()}
 function kick(s){if(rm.matches){ang+=s*TICK;return draw()}tgt=(mode===3?tgt:ang)+s*TICK;acc=0;mode=3;loop()}
 function loop(){if(raf)return;ft=performance.now();const f=now=>{const dt=Math.min(.05,(now-ft)/1000);ft=now;
   if(mode===2){om*=Math.exp(-dt*2.6);turn(om*dt,Math.abs(om));if(Math.abs(om)<1.2)settle()}
   if(mode===3){sp+=(220*(tgt-ang)-26*sp)*dt;ang+=sp*dt;hist.push({a:ang,t:now});if(Math.abs(tgt-ang)<.002&&Math.abs(sp)<.02){ang=tgt;mode=0}}
   draw();raf=(mode||hist.length)?requestAnimationFrame(f):0};raf=requestAnimationFrame(f)}
 const pt=e=>{const b=sv.getBoundingClientRect(),s=200/b.width;return[(e.clientX-b.left)*s-100,(e.clientY-b.top)*s-100]};
 sv.addEventListener('pointerdown',e=>{if(!max)return;const[x,y]=pt(e);if(Math.hypot(x,y)<DEAD)return;e.preventDefault();sv.focus({preventScroll:true});
  sv.setPointerCapture(e.pointerId);mode=1;acc=0;last=Math.atan2(y,x);lt=performance.now();om=0;sv.classList.add('gr');loop()});
 sv.addEventListener('pointermove',e=>{if(mode!==1)return;const[x,y]=pt(e),now=performance.now();if(Math.hypot(x,y)<DEAD){last=null;return}
  const a=Math.atan2(y,x);if(last===null){last=a;lt=now;return}let d=a-last;d-=Math.round(d/TAU)*TAU;
  const dt=Math.max(1,now-lt)/1000;om=om*.6+(d/dt)*.4;last=a;lt=now;turn(d,Math.abs(om))});
 const up=()=>{if(mode!==1)return;sv.classList.remove('gr');if(performance.now()-lt>90)om=0;if(!rm.matches&&Math.abs(om)>V_FLICK){mode=2;loop()}else settle()};
 sv.addEventListener('pointerup',up);sv.addEventListener('pointercancel',up);
 sv.addEventListener('keydown',e=>{if(!max)return;const k={ArrowUp:1,ArrowRight:1,ArrowDown:-1,ArrowLeft:-1,PageUp:10,PageDown:-10}[e.key];
  if(k){e.preventDefault();if(bump(step*k))kick(Math.sign(k));draw();return}
  if(e.key==='Home'||e.key==='End'){e.preventDefault();v=e.key==='Home'?0:max;ff.value=v;kick(e.key==='Home'?-1:1);draw()}});
 wr.addEventListener('click',e=>{const s=e.target.closest('[data-st]'),k=e.target.closest('[data-dk]');
  if(s){step=+s.dataset.st;wr.querySelectorAll('[data-st]').forEach(b=>b.classList.toggle('on',b===s));savePrefs()}
  if(k){if(k.dataset.dk==='max'){if(v<max){v=max;ff.value=v;kick(1)}}else{const n=+k.dataset.dk;if(bump(step*n))kick(n)}draw()}});
 ff.addEventListener('input',()=>{v=Math.max(0,Math.min(max,Math.round(+ff.value||0)));draw()});
 fq.addEventListener('input',()=>{max=Math.max(0,Math.round(+fq.value||0));if(v>max){v=max;ff.value=v}draw()});
 return{getStep:()=>step,setStep(n){if(![1,10,100].includes(+n))return;step=+n;wr.querySelectorAll('[data-st]').forEach(b=>b.classList.toggle('on',+b.dataset.st===step))},set(f,q){max=Math.max(0,Math.round(+q||0));base=v=Math.min(max,Math.max(0,Math.round(+f||0)));ang=tgt=-Math.PI/2;acc=0;mode=0;hist=[];draw()}};
})();

/* ===== ANIMAÇÃO DE ABERTURA (Início) =====
   Blocos isométricos dos módulos enviam dados pelas linhas até o bloco central (P);
   a tela entra no bloco e o painel aparece. Liga/desliga em Configurações. */
let ANIM=true,INTRO=false;
function introHTML(){
 const NSV=(x,y)=>`${x.toFixed(1)} ${y.toFixed(1)}`,P=(a,b)=>[(a-b)*.7071,(a+b)*.408];
 const blk=(x,y,w,h,top,sl,sr,inner,lb,d)=>{const L=P(-w/2,h/2),B=P(w/2,h/2),Rr=P(w/2,-h/2),T=P(-w/2,-h/2),D=9;
  return`<g transform="translate(${x} ${y})"><g class="tile" style="transition-delay:${d}ms">
  <path d="M${NSV(...L)}L${NSV(...B)}L${NSV(B[0],B[1]+D)}L${NSV(L[0],L[1]+D)}Z" fill="${sl}"/>
  <path d="M${NSV(...B)}L${NSV(...Rr)}L${NSV(Rr[0],Rr[1]+D)}L${NSV(B[0],B[1]+D)}Z" fill="${sr}"/>
  <path d="M${NSV(...T)}L${NSV(...Rr)}L${NSV(...B)}L${NSV(...L)}Z" fill="${top}"/>
  <g transform="matrix(.7071,.408,-.7071,.408,0,0)">${inner}</g>${lb?`<text class="tl" y="${B[1]+D+20}" text-anchor="middle">${lb}</text>`:''}</g></g>`};
 const ic=n=>`<g transform="rotate(-45) translate(-15.6 -15.6) scale(1.3)" fill="none" stroke="#0b2a7a" stroke-width="1.9" stroke-linecap="round" stroke-linejoin="round">${IC[n]}</g>`;
 const H=[560,140],E=i=>i===5?[H[0]+34,H[1]+20]:i===6?[H[0]+12,H[1]+27]:[H[0]-46+i*8,H[1]+4+i*4.5];
 const paths=[`M150 262C250 350 430 235 ${NSV(...E(0))}`,`M240 160C300 214 410 214 ${NSV(...E(1))}`,`M382 120C425 150 470 160 ${NSV(...E(2))}`,
  `M470 250C478 214 500 190 ${NSV(...E(3))}`,`M382 345C372 270 480 236 ${NSV(...E(4))}`,`M690 252C650 226 625 196 ${NSV(...E(5))}`,`M595 326C592 290 590 245 ${NSV(...E(6))}`];
 const W='#ffffff',S1='#d3def3',S2='#a9bbdf',emb=($('.emb')||{}).src||'';
 return`<div id="intro" role="img" aria-label="Animação de abertura: dados da produção entrando no sistema">
 <svg viewBox="95 60 650 360" preserveAspectRatio="xMidYMid meet" aria-hidden="true">
  <circle cx="420" cy="220" r="250" fill="rgba(255,255,255,.035)"/><circle cx="420" cy="220" r="170" fill="rgba(255,255,255,.035)"/>
  <g>${paths.map(d=>`<path class="ln" d="${d}"/>`).join('')}</g><g id="ipl"></g>
  ${blk(150,250,56,56,W,S1,S2,ic('pal'),'Estoque',0)}${blk(240,148,56,56,W,S1,S2,ic('op'),'Ordens de Produção',180)}
  ${blk(382,108,56,56,W,S1,S2,ic('gan'),'Planejamento',360)}${blk(690,240,56,56,W,S1,S2,ic('gau'),'Capacidade',540)}
  ${blk(382,333,56,56,W,S1,S2,ic('nut'),'Qualidade',720)}${blk(595,345,56,56,W,S1,S2,ic('db'),'Gestão de Dados',810)}
  ${blk(470,262,150,40,W,S1,S2,`<text font-size="12.5" font-weight="800" fill="#0b2a7a" text-anchor="middle" dominant-baseline="central" letter-spacing=".6">PPCP · PROJEART</text>`,'',900)}
  <ellipse class="rip" cx="${H[0]}" cy="${H[1]+4}" rx="56" ry="32"/><ellipse class="rip b" cx="${H[0]}" cy="${H[1]+4}" rx="56" ry="32"/>
  ${blk(H[0],H[1],72,72,'#2f6bff','#1d47c9','#16379e',`<rect x="-28" y="-28" width="56" height="56" rx="6" fill="#4b82ff"/>`,'',1080)}${emb?`<g transform="translate(${H[0]} ${H[1]-6})"><g class="tile" style="transition-delay:1250ms"><image href="${emb}" x="-23" y="-34" width="46" height="46"/></g></g>`:''}
 </svg>
 <div class="q">“Dados da produção conectados em um só lugar.”<small id="ist">Iniciando…</small></div></div>`}
function countUp(){document.querySelectorAll('#view .k .v,#view .dn b').forEach(el=>{const tx=el.textContent.trim(),m=tx.match(/^([\d.,\s\u00a0]+)(%?)$/);if(!m)return;const alvo=parseInt(m[1].replace(/\D/g,''),10);if(!(alvo>0)||alvo>1e9)return;const suf=m[2],t0=performance.now(),D=1100;
  (function f(now){const p=Math.min(1,(now-t0)/D),e=1-Math.pow(1-p,3);el.textContent=p<1?nf(alvo*e)+suf:tx;if(p<1&&el.isConnected)requestAnimationFrame(f)})(t0)})}
function runIntro(){const el=$('#intro'),vw=$('#view');if(!el)return;vw.classList.add('pre');vw.classList.remove('rv');
 const NSV='http://www.w3.org/2000/svg',ln=[...el.querySelectorAll('.ln')],tm=[],st=$('#ist');
 ln.forEach(p=>{p._L=p.getTotalLength();p.style.strokeDasharray=p._L;p.style.strokeDashoffset=p._L});
 const dots=ln.flatMap((p,i)=>[0,.5].map(o=>{const c=document.createElementNS(NSV,'circle');c.setAttribute('r','3.4');c.setAttribute('class','pl');c.style.opacity=0;$('#ipl').append(c);return{c,p,o:(o+i*.17)%1}}));
 requestAnimationFrame(()=>requestAnimationFrame(()=>el.classList.add('on')));
 tm.push(setTimeout(()=>ln.forEach((p,i)=>{p.style.transition=`stroke-dashoffset 1.4s ease-out ${i*160}ms`;p.style.strokeDashoffset=0}),1300));
 const msgs=['Conectando estoque…','Conectando ordens de produção…','Conectando planejamento…','Conectando capacidade…','Conectando qualidade…','Conectando gestão de dados…','Entrando no sistema…'];
 msgs.forEach((m,i)=>tm.push(setTimeout(()=>{if(st)st.textContent=TX(m)},1300+i*700)));
 const t0=performance.now();(function f(now){if(!el.isConnected||el.classList.contains('go'))return;const t=(now-t0)/1000;
  if(t>2.6)for(const d of dots){const u=((t-2.6)/1.3+d.o)%1,pt=d.p.getPointAtLength(u*d.p._L);d.c.setAttribute('cx',pt.x);d.c.setAttribute('cy',pt.y);d.c.style.opacity=Math.sin(u*Math.PI).toFixed(2)}
  requestAnimationFrame(f)})(t0);
 let fim=false;const entrar=rapido=>{if(fim)return;fim=true;tm.forEach(clearTimeout);document.removeEventListener('keydown',esc_);
  if(!el.isConnected)return vw.classList.remove('pre');
  el.classList.add('go');setTimeout(()=>{vw.classList.remove('pre');vw.classList.add('rv');countUp()},rapido?60:300);
  setTimeout(()=>{el.remove()},rapido?650:950);setTimeout(()=>vw.classList.remove('rv'),2200)};
 const esc_=()=>{};
 tm.push(setTimeout(()=>entrar(false),6300))}
/* MODAL OP */
$('#fc').innerHTML=PROC.map(p=>`<option value="${p}">${p}</option>`).join('');$('#fs').innerHTML=STS.map(p=>`<option value="${p}">${p}</option>`).join('');let eid=null;
function openOP(id){eid=id||null;const o=ops.find(x=>x.id===id)||{produto:'',qtde:'',feito:0,proc:PROC[0],prazo:addD(3),st:'Em aberto'};
 $('#dgt').textContent=id?'Editar '+id:'Nova ordem de produção';$('#fp').value=o.produto;$('#fq').value=o.qtde;$('#ff').value=o.feito;$('#fc').value=o.proc;$('#fd').value=o.prazo;$('#fs').value=o.st;$('#fx').classList.toggle('hide',!id||!(USER&&USER.adm));Dial.set(o.feito,o.qtde);applyI18n($('#dg'));$('#dg').showModal()}
$('#fn').onclick=()=>$('#dg').close();
$('#fx').onclick=async()=>{if(!confirmT('Excluir '+eid+'?'))return;const x=ops.find(o=>o.id===eid);const {error}=await SB.from('ops').delete().eq('id',eid);if(error)return falha(error);DB.log('ops',eid,'excluir',{produto:x&&x.produto});await DB.refresh();$('#dg').close();render();toast('OP excluída')};
$('#df').onsubmit=async e=>{e.preventDefault();const q=+$('#fq').value,f=Math.min(q,Math.max(0,+$('#ff').value||0));let s=$('#fs').value;
 if(!$('#fp').value.trim()||q<1||!$('#fd').value)return toast('Preencha produto, quantidade e prazo');
 if(f>=q)s='Concluída';else if(f>0&&s==='Em aberto')s='Em produção';else if(s==='Concluída'&&f<q)s='Em produção';
 const d={produto:$('#fp').value.trim(),qtde:q,feito:f,proc:$('#fc').value,prazo:$('#fd').value,st:s};let id=eid,ant=0;
 const bt=$('#fv');if(bt)bt.disabled=true;
 try{if(eid){const o=ops.find(o=>o.id===eid);ant=o?+o.feito||0:0;const {error}=await SB.from('ops').update(d).eq('id',eid);if(error)throw error}
  else{for(let t=0;t<3;t++){id='OP-'+(Math.max(1049,...ops.map(o=>+o.id.slice(3)||0))+1);const {error}=await SB.from('ops').insert({id,...d});if(!error)break;if(error.code!=='23505'||t===2)throw error;await DB.refresh()}}
  if(f!==ant){const r=await SB.from('apontamentos').insert({op_id:id,quantidade:f-ant,total_apos:f});if(r.error)throw r.error}
  DB.log('ops',id,eid?'editar':'criar',{produto:d.produto,qtde:q,feito:f,st:s});await DB.refresh();$('#dg').close();render();toast('OP salva')}
 catch(err){falha(err)}finally{if(bt)bt.disabled=false}};

document.addEventListener('click',e=>{if(e.target.closest('#tt1'))return setTheme(THEME==='dark'?'light':'dark');const t=e.target.closest('[data-th]');if(t)return setTheme(t.dataset.th);const g=e.target.closest('[data-lg]');if(g)return setLang(g.dataset.lg);
 if(e.target.closest('#gb'))return pop();if(!e.target.closest('#gp'))pop(false)});
document.addEventListener('keydown',e=>{if(e.key==='Escape'&&!$('#gp').classList.contains('hide')){pop(false);$('#gb').focus()}});
document.documentElement.lang=HL[LANG];document.documentElement.setAttribute('data-theme',THEME);document.title=TX('SISTEMA - PPCPM');applyI18n();markUI();
(async()=>{let tem=false;try{tem=!!AS.getItem('sb-zlbgiodxpywrqapjlldg-auth-token')}catch(e){}if(tem)coverIntro();
 try{if(!SB)throw 0;const {data}=await SB.auth.getSession();if(data&&data.session){const p=await perfilDe(data.session.user.id);if(p&&p.ativo){await enter(uObj(p),true);return}await SB.auth.signOut()}}catch(e){if(e)console.error(e)}
 const c=document.getElementById('intro');if(c&&!USER)c.remove()})();
