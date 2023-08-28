@echo off
ping -n 1 www.google.com > nul && echo connected || echo not connected
