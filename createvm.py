"""
Python program for create VMs in Vcenter
"""
from pyVim.connect import SmartConnectNoSSL, Disconnect
from pyVim import connect
from pyVmomi import vim, vmodl
from tools import tasks
import atexit
import json
#导入配置参数
f = open("linux-guest.json", encoding="utf-8")
guest = json.load(f)

def get_obj(content,vimtype,name):
    obj = None
    container = content.viewManager.CreateContainerView(
        content.rootFolder, vimtype, True)
    for c in container.view:
        if c.name==name:
            obj=c
            break
    return obj

def create_vm(name,si,vm_folder,resource_pool,datastore,network):
	vm_name = name
	datastore_path = "["+datastore+"]/"+vm_name+"/"+vm_name+".vmx"
	vmx_file = vim.vm.FileInfo(logDirectory=None,snapshotDirectory=None,suspendDirectory=None,vmPathName=datastore_path)
	configspec = vim.vm.ConfigSpec(name=vm_name,memoryMB=int(guest['ramsize']),numCPUs=int(guest['vcpus']),
                                   guestId=guest['guestID'],version=guest['version'],files=vmx_file,
                                   cpuHotAddEnabled=True, memoryHotAddEnabled=True)
##添加虚拟设备nic
	nic_spec = vim.vm.device.VirtualDeviceSpec()
	nic_spec.operation = vim.vm.device.VirtualDeviceSpec.Operation.add
	nic_spec.device = vim.vm.device.VirtualE1000()
	nic_spec.device.deviceInfo = vim.Description()
	nic_spec.device.backing = \
		vim.vm.device.VirtualEthernetCard.NetworkBackingInfo()
	nic_spec.device.backing.useAutoDetect = False
	content = si.RetrieveContent()
	nic_spec.device.backing.network = get_obj(content, [vim.Network], network)
	nic_spec.device.backing.deviceName = network
	nic_spec.device.connectable = vim.vm.device.VirtualDevice.ConnectInfo()
	nic_spec.device.connectable.startConnected = True
	nic_spec.device.connectable.allowGuestControl = True
	nic_spec.device.connectable.connected = False
	nic_spec.device.connectable.status = 'untried'
	nic_spec.device.wakeOnLanEnabled = True
	nic_spec.device.addressType = 'assigned'
	configspec.deviceChange.append(nic_spec)
	print("网卡添加成功")
##添加sisc控制器
	scsictl_spec = vim.vm.device.VirtualDeviceSpec()
	scsictl_spec.operation = vim.vm.device.VirtualDeviceSpec.Operation.add
	scsictl_spec.device = vim.vm.device.VirtualLsiLogicController()
	scsictl_spec.device.deviceInfo = vim.Description()
	scsictl_spec.device.slotInfo = vim.vm.device.VirtualDevice.PciBusSlotInfo()
	scsictl_spec.device.slotInfo.pciSlotNumber = 16
	scsictl_spec.device.controllerKey = 100
	scsictl_spec.device.unitNumber = 3
	scsictl_spec.device.busNumber = 0
	scsictl_spec.device.hotAddRemove = True
	scsictl_spec.device.sharedBus = 'noSharing'
	scsictl_spec.device.scsiCtlrUnitNumber = 7
	configspec.deviceChange.append(scsictl_spec)
	print("scsi控制器添加成功")
	print("Creating VM{}...".format(vm_name))
	task = vm_folder.CreateVM_Task(config=configspec,pool=resource_pool)
	tasks.wait_for_tasks(si,[task])

def add_disk(vm, si, disk_size, disk_type):
	spec = vim.vm.ConfigSpec()
	# get all disks on a VM, set unit_number to the next available
	unit_number = 0
	for dev in vm.config.hardware.device:
		if hasattr(dev.backing, 'fileName'):
			unit_number = int(dev.unitNumber) + 1
			# scsi controller unit_number  默认为7
			if unit_number == 7:
				unit_number += 1
		if isinstance(dev, vim.vm.device.VirtualSCSIController):
			controller = dev
	# 添加磁盘
	dev_changes = []
	new_disk_kb = int(disk_size) * 1024 * 1024
	disk_spec = vim.vm.device.VirtualDeviceSpec()
	disk_spec.fileOperation = "create"
	disk_spec.operation = vim.vm.device.VirtualDeviceSpec.Operation.add
	disk_spec.device = vim.vm.device.VirtualDisk()
	disk_spec.device.backing = \
		vim.vm.device.VirtualDisk.FlatVer2BackingInfo()
	if disk_type == 'thin':
		disk_spec.device.backing.thinProvisioned = True
	disk_spec.device.backing.diskMode = 'persistent'
	disk_spec.device.unitNumber = unit_number
	disk_spec.device.capacityInKB = new_disk_kb
	disk_spec.device.controllerKey = controller.key
	dev_changes.append(disk_spec)
	spec.deviceChange = dev_changes
	vm.ReconfigVM_Task(spec=spec)

def check_vm_cdrom(vm):
    for device in vm.config.hardware.device:
        if isinstance(device,vim.vm.device.VirtualCdrom):
            return device
    return None

def find_free_ide_controller(vm):
    for dev in vm.config.hardware.device:
        if isinstance(dev,vim.vm.device.VirtualIDEController):
            if len(dev.device)<2:
                return dev
    return None

def new_cdrom_spec(controller_key,backing):
    connectable = vim.vm.device.VirtualDevice.ConnectInfo()
    connectable.allowGuestControl = True
    connectable.startConnected = True
    cdrom = vim.vm.device.VirtualCdrom()
    cdrom.controllerKey = controller_key
    cdrom.key = -1
    cdrom.connectable = connectable
    cdrom.backing = backing
    return cdrom

def main():
	si = connect.SmartConnectNoSSL(host=guest['host'],
                     user=guest['user'],
                     pwd=guest['password'],
                     port=int(guest['port']))
	if si:
		print("连接成功")
	atexit.register(Disconnect, si)
	content = si.RetrieveContent()
	datacenter = content.rootFolder.childEntity[0]
	vmfolder = datacenter.vmFolder
	resource_pool = get_obj(content,[vim.ResourcePool],'chen.zilong')
	ds =guest['datastore']	#数据存储路径
	name=guest['vmname']	#虚拟机名称
	network = guest['network']
	disk_type = guest['disk_type']
	disk_size = guest['disk_size']
	#创建虚拟机
	create_vm(name,si,vmfolder,resource_pool,ds,network)
	print("创建成功")
	#获得创建的虚拟机
	vm = get_obj(content,[vim.VirtualMachine],name)
	#添加磁盘
	add_disk(vm,si,disk_size,disk_type)
	print("磁盘添加成功")
	#添加CD-ROM
	iso = guest['isofile']
	controller = find_free_ide_controller(vm)
	if controller is None:
		raise Exception('Failed to find a free slot on the IDE controller')
	cdrom = check_vm_cdrom(vm)
	if iso is not None:
		deviceSpec = vim.vm.device.VirtualDeviceSpec()
		if cdrom is None:
			print("adding a new cd-rom")
			backing = vim.vm.device.VirtualCdrom.IsoBackingInfo(fileName=iso)
			cdrom = new_cdrom_spec(controller.key, backing)
			deviceSpec.operation = vim.vm.device.VirtualDeviceSpec.Operation.add
		else:
			print("Updating a old cd-rom")
			backing = vim.vm.device.VirtualCdrom.IsoBackingInfo(fileName=iso)
			cdrom.backing = backing
			deviceSpec.operation = vim.vm.device.VirtualDeviceSpec.Operation.edit
		deviceSpec.device = cdrom
		configSpec = vim.vm.ConfigSpec(deviceChange=[deviceSpec])
		vm.ReconfigVM_Task(spec=configSpec)
	##开机
	# task = vm.PowerOn()
	# tasks.wait_for_tasks(si, [task])

# Start program
if __name__ == "__main__":
    main()





