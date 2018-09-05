import paramiko
host ='10.128.1.17'
port = 22
user = 'root'
pwd = '123456'
##实现客户端与服务器中虚拟机文件的传输
transport = paramiko.Transport((host, port))
transport.connect(username=user, password=pwd)
sftp = paramiko.SFTPClient.from_transport(transport)
sftp.put('centos6.5-tests\\helloworld.c', '/tmp/helloworld.c')
sftp.put('centos6.5-tests\\test_centos.sh', '/tmp/test_centos.sh')
print("测试脚本上传成功")
transport.close()


#创建SSH对象
ssh = paramiko.SSHClient()
# 允许连接不在know_hosts文件中的主机
ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())#第一次登录的认证信息
# 连接服务器
ssh.connect(hostname=host, port=port, username=user, password=pwd)
# 执行命令,先更改权限，再执行
ssh.exec_command('chmod 777 /tmp/test_centos.sh')
stdin,stdout,stderr = ssh.exec_command('/tmp/test_centos.sh')
# 获取命令结果
res,err = stdout.read(),stderr.read()
result = res if res else err
print(result.decode())
# 关闭连接
ssh.close()