@echo off
ping -n 1 www.google.com > nul && echo online || echo not online
