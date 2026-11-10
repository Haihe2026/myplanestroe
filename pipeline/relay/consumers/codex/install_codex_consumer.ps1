param(
    [Parameter(Mandatory=$true)][string]$SchedulerRoot,
    [Parameter(Mandatory=$true)][string]$Pythonw
)
$ErrorActionPreference = 'Stop'
$root = (Resolve-Path -LiteralPath $SchedulerRoot).Path
$python = (Resolve-Path -LiteralPath $Pythonw).Path
$guard = Join-Path $root 'watch_codex_consumer.py'
if (-not (Test-Path -LiteralPath $guard -PathType Leaf)) { throw 'Consumer supervisor is missing' }
$startup = Join-Path ([Environment]::GetFolderPath('Startup')) 'SkillRelay-CodexConsumer.vbs'
$launch = 'Set shell = CreateObject("WScript.Shell")' + "`r`n" + 'shell.Run """' + $python + '"" ""' + $guard + '""", 0, False' + "`r`n"
[IO.File]::WriteAllText($startup, $launch, [Text.Encoding]::Unicode)
[IO.File]::WriteAllText((Join-Path $root '����Codex���շ�.vbs'), $launch, [Text.Encoding]::Unicode)
$task = 'SkillRelay-CodexConsumer-Recovery'
$action = New-ScheduledTaskAction -Execute $python -Argument ('"' + $guard + '"') -WorkingDirectory $root
$trigger = New-ScheduledTaskTrigger -Once -At (Get-Date).AddMinutes(1) -RepetitionInterval (New-TimeSpan -Minutes 1)
$principal = New-ScheduledTaskPrincipal -UserId ([Security.Principal.WindowsIdentity]::GetCurrent().Name) -LogonType Interactive -RunLevel Limited
$settings = New-ScheduledTaskSettingsSet -MultipleInstances IgnoreNew -AllowStartIfOnBatteries -DontStopIfGoingOnBatteries -ExecutionTimeLimit ([TimeSpan]::Zero) -RestartCount 3 -RestartInterval (New-TimeSpan -Minutes 1)
try {
    Register-ScheduledTask -TaskName $task -Action $action -Trigger $trigger -Principal $principal -Settings $settings -Force -ErrorAction Stop | Out-Null
    Start-ScheduledTask -TaskName $task -ErrorAction Stop
    Get-ScheduledTask -TaskName $task | Select-Object TaskName,State
} catch {
    Write-Warning ('Windows task registration unavailable. Using current-user startup supervisor. ' + $_.Exception.GetType().Name)
    Start-Process -FilePath $python -ArgumentList ('"' + $guard + '"') -WorkingDirectory $root -WindowStyle Hidden
}
