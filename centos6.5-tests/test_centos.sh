#!/bin/sh

printf "测试yum命令是否正常安装与卸载\n"
yum -y install w3m
yum -y remove w3m

printf "列出当前系统运行的进程\n"
ps

printf "列出io状态\n"
iostat

printf "列出内存使用情况\n"
vmstat

printf "测试gcc编译器\n"
gcc -o helloworld helloworld.c

printf "测试文件的基本操作\n"
printf "创建文件夹test-file\n"
mkdir test-file
printf "创建文件test1.txt\n"
touch test1.txt
printf "复制文件test1.txt到文件夹test-file\n"
cp test1.txt  test-file
printf "重命名文件test1.txt为test2.txt\n"
mv test1.txt test2.txt
printf "删除文件test2.txt\n"
rm test2.txt
printf "删除文件夹test-file\n"
rm -rf test-file



