[CmdletBinding()]
param(
    [Parameter(Mandatory = $true)]
    [ValidateSet('snapshot', 'live')]
    [string]$Mode
)

$ErrorActionPreference = 'Stop'
$snapshotPath = 'C:\ProgramData\NexusChat\infra-snapshot.json'

if ($Mode -eq 'snapshot') {
    if (-not (Test-Path -LiteralPath $snapshotPath -PathType Leaf)) {
        throw 'The managed Windows infrastructure snapshot is unavailable.'
    }
    Get-Content -Raw -LiteralPath $snapshotPath
    exit 0
}

$os = Get-CimInstance -ClassName Win32_OperatingSystem
$computer = Get-CimInstance -ClassName Win32_ComputerSystem
$cpu = Get-CimInstance -ClassName Win32_Processor |
    Measure-Object -Property LoadPercentage -Average
$disks = Get-CimInstance -ClassName Win32_LogicalDisk -Filter 'DriveType=3' |
    ForEach-Object {
        [ordered]@{
            device = $_.DeviceID
            total_bytes = [int64]$_.Size
            free_bytes = [int64]$_.FreeSpace
            used_percent = if ($_.Size) { [math]::Round((1 - ($_.FreeSpace / $_.Size)) * 100, 1) } else { 0 }
        }
    }
$ports = Get-NetTCPConnection -State Listen -ErrorAction SilentlyContinue |
    Select-Object -ExpandProperty LocalPort -Unique |
    Sort-Object |
    Select-Object -First 256
$serviceNames = @('W3SVC', 'WinRM', 'MSSQLSERVER', 'Spooler')
$services = foreach ($serviceName in $serviceNames) {
    $service = Get-Service -Name $serviceName -ErrorAction SilentlyContinue
    if ($null -ne $service) {
        [ordered]@{ name = $service.Name; status = $service.Status.ToString() }
    }
}
$since = (Get-Date).AddHours(-24)
$eventCounts = Get-WinEvent -FilterHashtable @{ LogName = 'System'; Level = 1, 2; StartTime = $since } -ErrorAction SilentlyContinue |
    Group-Object -Property LevelDisplayName |
    ForEach-Object { [ordered]@{ level = $_.Name; count = $_.Count } }
$pendingRename = Get-ItemProperty -LiteralPath 'HKLM:\SYSTEM\CurrentControlSet\Control\Session Manager' `
    -Name PendingFileRenameOperations -ErrorAction SilentlyContinue
$rebootPending = (Test-Path -LiteralPath 'HKLM:\SOFTWARE\Microsoft\Windows\CurrentVersion\WindowsUpdate\Auto Update\RebootRequired') -or
    ($null -ne $pendingRename)

$result = [ordered]@{
    generated_at = (Get-Date).ToUniversalTime().ToString('o')
    hostname = $env:COMPUTERNAME
    platform = 'windows'
    mode = 'live'
    scope = 'sanitized_read_only'
    os = [ordered]@{ caption = $os.Caption; version = $os.Version; build = $os.BuildNumber }
    uptime_seconds = [int64]((Get-Date) - $os.LastBootUpTime).TotalSeconds
    cpu = [ordered]@{ load_percent = [math]::Round($cpu.Average, 1) }
    memory = [ordered]@{
        total_bytes = [int64]$computer.TotalPhysicalMemory
        available_bytes = [int64]$os.FreePhysicalMemory * 1KB
        used_percent = [math]::Round((1 - (($os.FreePhysicalMemory * 1KB) / $computer.TotalPhysicalMemory)) * 100, 1)
    }
    disks = @($disks)
    listening_tcp_ports = @($ports)
    services = @($services)
    system_events_24h = @($eventCounts)
    reboot_pending = [bool]$rebootPending
}

$result | ConvertTo-Json -Depth 6 -Compress
