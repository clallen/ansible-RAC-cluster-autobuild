#!/usr/bin/python

import os, subprocess, pwd, grp, stat
from stat import S_IMODE

GAWK_CODE = 'BEGIN { RS=":" } { if (NR==2) { sect_per_cyl=$11\ntotal_cyl=$17 } } END { first_sect=sect_per_cyl\nsect_count=(sect_per_cyl * total_cyl - first_sect)\nprint "0 0 00 "first_sect" "sect_count }'

def main():
    module = AnsibleModule(argument_spec = dict(), supports_check_mode = True)

    changed = False
    msg = []

    for index in range(10, 98):
        device = "/dev/rdsk/c1d"+str(index)+"s2"
        if not os.path.exists(device):
            continue
        msg.append("Checking disk "+device)
        # label disk
        code = subprocess.call(["/usr/sbin/prtvtoc", device])
        if code != 0:
            msg.append("Labelling disk")
            if not module.check_mode:
                subprocess.call(["/usr/sbin/format", "-L", "vtoc", "-d", os.path.basename(device)[:-2]])
                changed = True
        # create whole disk partition table
        linecount = subprocess.check_output("/usr/sbin/prtvtoc "+device+" | /usr/bin/grep -v ^* | wc -l", shell = True)
        linecount.strip()
        if int(linecount) != 2:
            msg.append("Creating whole disk partition table")
            if not module.check_mode:
                subprocess.call("/usr/sbin/prtvtoc "+device+" | gawk '"+GAWK_CODE+"' | /usr/sbin/fmthard -s - "+device, shell = True)
                changed = True
        # set owner/perms
        pdevice = device.replace("s2", "s0")
        grid_uid = pwd.getpwnam("grid").pw_uid
        grid_gid = grp.getgrnam("dba").gr_gid
        stat = os.stat(pdevice)
        if stat.st_uid != grid_uid:
            msg.append("Setting owner to grid")
            if not module.check_mode:
                os.chown(pdevice, grid_uid, -1)
                changed = True
        if stat.st_gid != grid_gid:
            msg.append("Setting group to dba")
            if not module.check_mode:
                os.chown(pdevice, -1, grid_gid)
                changed = True
        filemode = oct(S_IMODE(os.stat(pdevice).st_mode))
        if filemode != "0660":
            msg.append("Setting permissions to 660")
            if not module.check_mode:
                os.chmod(pdevice, 0660)
                changed = True

    module.exit_json(changed = changed, msg = " | ".join(msg))


from ansible.module_utils.basic import *
if __name__ == "__main__":
    main()