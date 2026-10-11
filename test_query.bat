@echo off
chcp 65001 > nul

echo Testing parameter parsing...
echo Arg1: %1
echo Arg2: %2
echo Arg3: %3
echo Arg4: %4

if "%1"=="query" (
    echo Query mode detected
    shift
    echo Stock code: %1
) else (
    echo Not query mode
)

pause