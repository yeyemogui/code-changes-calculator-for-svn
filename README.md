# code-changes-calculator-for-svn
Code has been tested under python 2.6.6

V0.1 update:
New option -f is added to allow calculation of code lines which introduced by specific feature. -f option can be used together with -n

--------------------------------------------------------
v0.0: 
This tool can be used to calculate the changed lines introduced by authors. If you want to calculate data for a list of authors, and you don't know the svn account of them, below sample command can be used to retrieve the author list:
./parser.py -c fullNameList.txt -t {2019-06-01}:{2020-03-20} -s svnRepoAddr
You can find the created fullNameList.txt, and modify it.

Below sample command can be used to calculate changed lines:
./parser.py -t {2019-08-01}:{2020-03-20} -s svnRepoAddr -n authorList.txt -j 52

