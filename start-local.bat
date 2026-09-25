@echo off
title CandidateX Local Server
powershell -ExecutionPolicy Bypass -File "%~dp0start-local.ps1" %*
pause
