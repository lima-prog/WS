# Cria os atalhos do SISTEMA - PPCPM (Area de Trabalho, Menu Iniciar e, se pedido, iniciar com o Windows)
param([string]$Pasta, [switch]$Inicio, [switch]$TirarInicio)
$shell = New-Object -ComObject WScript.Shell
function Atalho($arquivo, $argumentos) {
  $s = $shell.CreateShortcut($arquivo)
  $s.TargetPath = Join-Path $Pasta 'ABRIR_SISTEMA.bat'
  $s.Arguments = $argumentos
  $s.WorkingDirectory = $Pasta
  $s.IconLocation = (Join-Path $Pasta 'ppcpm\web\icone.ico') + ',0'
  $s.WindowStyle = 7
  $s.Description = 'SISTEMA - PPCPM | Grupo Projeart'
  $s.Save()
}
$inicioWin = Join-Path ([Environment]::GetFolderPath('Startup')) 'SISTEMA - PPCPM.lnk'
if ($Inicio) { Atalho $inicioWin '--sem-navegador'; Write-Host 'Vai abrir junto com o Windows.'; exit }
if ($TirarInicio) { if (Test-Path $inicioWin) { Remove-Item $inicioWin }; exit }
Atalho (Join-Path ([Environment]::GetFolderPath('Desktop')) 'SISTEMA - PPCPM.lnk') ''
$menu = Join-Path ([Environment]::GetFolderPath('Programs')) 'SISTEMA - PPCPM.lnk'
Atalho $menu ''
Write-Host 'Atalhos criados: Area de Trabalho e Menu Iniciar.'
