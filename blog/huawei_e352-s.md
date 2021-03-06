title: Getting a Huawei E352s-5 to work with Linux
date: 2013-04-27 16:18
tags: linux
category: linux
slug: huawei_e352s5
author: Philipp Wagner

This is just a quick note on how to get a Huawei E352s-5 working under Linux. 

## switching into modem mode ##

If you have inserted your SIM card, plugged in the Huawei E352s-5 stick and your distribution recognized it... you can stop reading here. But if you 
are on an old distribution like I am, you'll probably need to use [usb_modeswitch](http://www.draisberghof.de/usb_modeswitch/) to get it working. 

First of all, let's see what ``dmesg`` says after inserting the stick:

```
philipp@mango:~$ dmesg
...
[   48.220072] usb 2-5: new high speed USB device using ehci_hcd and address 4
[   48.362048] scsi5 : usb-storage 2-5:1.4
[   48.367660] scsi6 : usb-storage 2-5:1.5
[   49.365716] scsi 5:0:0:0: CD-ROM            HUAWEI   Mass Storage     2.31 PQ: 0 ANSI: 2
[   49.368325] sr1: scsi-1 drive
[   49.368854] sr 5:0:0:0: Attached scsi CD-ROM sr1
[   49.369011] sr 5:0:0:0: Attached scsi generic sg2 type 5
[   49.372964] scsi 6:0:0:0: Direct-Access     HUAWEI   SD Storage       2.31 PQ: 0 ANSI: 2
[   49.374988] sd 6:0:0:0: Attached scsi generic sg3 type 0
[   49.380995] sd 6:0:0:0: [sdb] Attached SCSI removable disk
[   49.511962] ISO 9660 Extensions: Microsoft Joliet Level 1
[   49.542715] ISOFS: changing to secondary root
```

The device seems to register as an USB Mass Storage device and not as a modem, running ``lsusb`` shows us the the Vendor and Product ID:

```
philipp@mango:~$ lsusb
...
Bus 002 Device 008: ID 12d1:14fe Huawei Technologies Co., Ltd. 
```

Great! So let's see how to switch the device into its Modem mode. 

There is a nice open source project called [usb_modeswitch](http://www.draisberghof.de/usb_modeswitch), which does the job.

First of all let's get ``libusb-dev``, since we may need it for compiling:

```sh
sudo apt-get install libusb-dev
```

Next we'll download, unpack and install the most recent versions of ``usb_modeswitch`` and its ``usb_modeswitch-data``, available at:

* [http://www.draisberghof.de/usb_modeswitch](http://www.draisberghof.de/usb_modeswitch)

Installing is easy, I guess you are familiar with the commands:

```sh
# Download sources:
wget http://www.draisberghof.de/usb_modeswitch/usb-modeswitch-1.2.5.tar.bz2
# Extract the source:
tar xjf usb-modeswitch-1.2.5.tar.bz2
# Change directory:
cd usb-modeswitch-1.2.5
# Install it:
sudo make install
```

Do the same for the [usb_modeswitch-data](http://www.draisberghof.de/usb_modeswitch/), which contains a lot of udev scripts, that *might* cover your hardware already:

```sh 
wget http://www.draisberghof.de/usb_modeswitch/usb-modeswitch-data-20121109.tar.bz2
tar xjf usb-modeswitch-data-20121109.tar.bz2
cd usb-modeswitch-data-20121109
sudo make install
```

The new [usb_modeswitch](http://www.draisberghof.de/usb_modeswitch/) overrides the old version, so there's no need to take care about old installations! 
With [usb_modeswitch](http://www.draisberghof.de/usb_modeswitch/) it's easy to switch the Huawei E352-s into the Modem mode. A quick research reveals the 
switching command, I guess it's the packet Windows sends to the device in order to switch modes. 

I really don't feel the need to sniff it by myself (you have to run the commands as root):

```sh
usb_modeswitch -v 12d1 -p 14fe -M '55534243123456780000000000000011062000000100000000000000000000' 
```

Now running ``lsusb`` reveals a new Product ID:

```
philipp@mango:~$ lsusb
...
Bus 002 Device 022: ID 12d1:1506 Huawei Technologies Co., Ltd
```

Using the ``option`` module should register the modem:

```sh
modprobe option
echo "12d1 1506" > /sys/bus/usb-serial/drivers/option1/new_id
```

Running ``dmesg`` (or looking at ``/var/log/messages`` if you prefer) reveals:

```
philipp@mango:~$ dmesg
...
[ 1471.905063] usb 2-5: new high speed USB device using ehci_hcd and address 12
[ 1472.039036] option 2-5:1.0: GSM modem (1-port) converter detected
[ 1472.039214] usb 2-5: GSM modem (1-port) converter now attached to ttyUSB0
[ 1472.039374] option 2-5:1.1: GSM modem (1-port) converter detected
[ 1472.039522] usb 2-5: GSM modem (1-port) converter now attached to ttyUSB1
[ 1472.039647] option 2-5:1.2: GSM modem (1-port) converter detected
[ 1472.039751] usb 2-5: GSM modem (1-port) converter now attached to ttyUSB2
[ 1472.039893] option 2-5:1.3: GSM modem (1-port) converter detected
[ 1472.039997] usb 2-5: GSM modem (1-port) converter now attached to ttyUSB3
[ 1472.040173] option 2-5:1.4: GSM modem (1-port) converter detected
[ 1472.040268] usb 2-5: GSM modem (1-port) converter now attached to ttyUSB4
[ 1472.040404] option 2-5:1.5: GSM modem (1-port) converter detected
[ 1472.040496] usb 2-5: GSM modem (1-port) converter now attached to ttyUSB5
```

The modem should be usable by now and your network-manager should ask you for the PIN to unlock the device. 

Congratulations!

## udev rules ##

If you don't want to impress people by remembering these cryptic lines, you could write two ``udev`` rules to execute these commands whenever the device is 
added to the USB subsystem. Store it to ``/etc/udev/rules.d/70-huawei_e352.rules`` for example.

**Filename** ``/etc/udev/rules.d/70-huawei_e352.rules``:

```
ACTION=="add", SUBSYSTEM=="usb", ATTRS{idVendor}=="12d1", ATTRS{idProduct}=="14fe", RUN+="/usr/sbin/usb_modeswitch -v 12d1 -p 14fe -M '55534243123456780000000000000011062000000100000000000000000000'"
ACTION=="add", SUBSYSTEM=="usb", ATTRS{idVendor}=="12d1", ATTRS{idProduct}=="14fe", RUN+="/bin/bash -c 'modprobe option && echo 12d1 1506 > /sys/bus/usb-serial/drivers/option1/new_id'"
```

And reload the rules:

```
udevadm control --reload-rules
```

And that's it basically! Your stick should now be put into Modem mode automatically, whenever you plug it in.