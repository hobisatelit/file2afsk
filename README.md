# file2afsk
Create AFSK 1200 modulated WAV audio from a binary file to be transmitted via a handheld FM radio, and vice versa. Example: send and receive SSDV image over AFSK 1200 modulation from terestrial or VR satellites

### Dependencies:
Debian/Ubuntu Linux
```bash
sudo apt update
sudo apt install python3 direwolf sox git pavucontrol
```
### Optional:
install ssdv. look at [this link for detailed howto](https://github.com/daniestevez/ssdv)

### Download the script:
```bash
cd ~
git clone https://github.com/hobisatelit/file2afsk.git && cd file2afsk
chmod 755 tx.py rx.py
```
### Configuration:
#### Config Callsigner
edit tx.py, change SRC_CALL = "ABC" with your actual callsigner 
#### Config Pavucontrol
You only need to set this up once. The goal is for the sox application (audio recorder) and direwolf (KISS server) to be able to listen to the audio output from the speakers or line out of the computer.

Open three terminal 

on first terminal run Direwolf KISS server
```bash
cd ~/file2afsk
direwolf -c direwolf.conf
```

on second terminal run
```bash
sox -d -r 44100 -c 1 /dev/null
```

on third terminal run
```bash
pavucontrol
```
look at recording tab, you will see direwolf app and sox there, please change capture to monitor mode both of them. and then you can close both app with press ctrl+c on each.

### How to convert file into WAV  
Run Direwolf KISS server
```bash
cd ~/file2afsk
direwolf -c direwolf.conf
```
on another terminal run
```bash
cd ~/file2afsk
./tx.py image.bin
```
### How to convert WAV into file
```bash
cd ~/file2afsk
./rx.py
```
play your recorded wav file or SDR, and the rx.py script will detect the file inside the sound. when finish, prest ctrl+c. the binary file will be saved as .bin file in same directory

### How to encode JPG file into SSDV bin
```bash
ssdv -e -q 1 image.jpg image.bin
```
### How to decode SSDV bin file into JPG
```bash
ssdv -d image.bin image.jpg
```
