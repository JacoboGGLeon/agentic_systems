# Sesión AWS prestada y complemento ADA · 2.1.4

Input: una sesión boto3 ya preparada, modelo y región. Proceso: validar runtime,
compilar el Agent e inspeccionar configuración. Output: informe sin credenciales
y alcance configuration-only. [Notebook](01_aws_session.ipynb) · [Código](example.py).

El ejemplo usa claves fixture explícitas para no consultar credenciales ni
metadatos. No crea clientes ni invoca modelos. En ADA se entrega al mismo runtime
la sesión que preparó la plataforma; la gramática Agent/System no cambia.

Requiere los wheels locales SDK y agentic-systems-ada dev8, más boto3. El
complemento no se instala con all. Su diagnóstico no repara variables ni valida
identidad/acceso. Las regresiones de los tres actores usan transporte simulado;
AWS IAM y ADA IAM reales continúan pendientes.

Dentro del toolkit, las invocaciones que comparten una sesión se serializan.
La coordinación con usos externos y su lifetime corresponden al propietario;
la sesión no se cierra ni se guarda en Context, Memory, estado o evidencia.
