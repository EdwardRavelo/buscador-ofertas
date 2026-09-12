' Lanza actualizar.bat SIN ventana. Es lo que ejecuta la tarea programada.
'
' Por que existe: si la tarea llama al .bat directo, Windows abre una consola
' negra en primer plano cada manana a las 09:00, encima de lo que estes haciendo.
' WScript.Shell.Run con estilo de ventana 0 la corre oculta.
'
' Por que NO se resolvio con "Ejecutar aunque el usuario no haya iniciado sesion"
' (que tambien oculta la ventana): el git push de actualizar.bat usa la credencial
' guardada en el Credential Manager de Windows, que es de la sesion del usuario.
' Fuera de esa sesion el deploy se rompe. Ver ESTADO.md, Fase 5.
'
' Para correrlo a mano: wscript actualizar-silencioso.vbs

Set shell = CreateObject("WScript.Shell")
Set fso = CreateObject("Scripting.FileSystemObject")

carpeta = fso.GetParentFolderName(WScript.ScriptFullName)
shell.CurrentDirectory = carpeta

' 0 = ventana oculta. True = esperar a que termine, para poder devolver su
' codigo de salida: sin eso la tarea programada informa siempre exito.
codigo = shell.Run("""" & carpeta & "\actualizar.bat""", 0, True)

WScript.Quit codigo
