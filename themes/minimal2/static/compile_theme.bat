@echo off

:: Copyright (c) Philipp Wagner. All rights reserved.
:: Licensed under the MIT license. See LICENSE file in the project root for full license information.

set SASSC_EXECUTABLE="D:\applications\sassc\sassc.exe"

%SASSC_EXECUTABLE% -t expanded ./scss/theme.scss > ./css/theme.css

:end
pause