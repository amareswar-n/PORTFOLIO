@echo off
REM Create branch (ignore error if it already exists)
git checkout -b logo-art1 2>nul
IF ERRORLEVEL 1 git checkout logo-art1

REM Create a file so we can commit
echo Legacy commit from Feb 11, 2015> legacy.txt
git add legacy.txt

REM Set backdated commit time
set GIT_AUTHOR_DATE=2015-02-11 10:00:00
set GIT_COMMITTER_DATE=2015-02-11 10:00:00

git commit -m "generate logo art"

echo.
echo Done. Now publish the branch in GitHub Desktop.
pause
