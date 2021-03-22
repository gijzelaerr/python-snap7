$dll_dir = $args[0]
New-Item -ItemType Directory wheelhouse
Set-Location dist
$wheels = Get-ChildItem *.whl
foreach ($wheelname in $wheels) {
    $dirname = -join($wheelname, "-dir")
    $unpack_string = $(python3 -m wheel unpack $wheelname -d $dirname)
    $unpack_string -match ".*: (?<pkgname>.*)...Ok"
    $packagename = $matches['pkgname']
    $libdir = -join($packagename,"\snap7\lib")
    New-Item -ItemType Directory -Path $libdir
    Copy-Item ..\snap7-full-1.4.2\release\Windows\$dll_dir\snap7.dll $libdir
    python3 -m wheel pack $packagename -d ..\wheelhouse
    Remove-Item $dirname -Force -Recurse
}