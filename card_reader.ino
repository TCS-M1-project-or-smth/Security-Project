// Arduino code
#include <SPI.h>
#include <MFRC522.h>

#define SS_PIN 10
#define RST_PIN 9
#define BUZZER_PIN 8
MFRC522 mfrc522(SS_PIN, RST_PIN );

uint32_t pyn;
struct {
  uint32_t d;
  uint32_t n;
} privkey;

// Modular exponentiation for RSA (https://stackoverflow.com/questions/52063315/modular-exponentiation-overflows-when-using-multiple-of-two-uint-32-numbers)
uint32_t modadd(uint32_t a, uint32_t b, uint32_t mod) {
    a %= mod;    // precondition -- might not be needed if the caller can guarentee it.
    b %= mod;    // precondition -- might not be needed if the caller can guarentee it

    a += b;
    if (a >= mod || a < b) a -= mod;
    return a;
}
uint32_t modmult(uint32_t a,uint32_t b,uint32_t mod) {

    if (a == 0 || b < mod / a)
        return ((uint32_t)a*b)%mod;
    uint32_t sum;
    sum = 0;
    while(b>0)
    {
        if(b&1)
            sum = modadd(sum, a, mod);
        a = modadd(a, a, mod);
        b>>=1;
    }
    return sum;
}
uint32_t modpow( uint32_t a,uint32_t b,uint32_t mod) {

    uint32_t product,pseq;
    product=1;
    pseq=a%mod;
    while(b>0)
    {
        if(b&1)
            product=modmult(product,pseq,mod);
        pseq=modmult(pseq,pseq,mod);
        b>>=1;
    }
    return product;
}

uint32_t ui32_le(uint8_t *b) {
  return (b[3] << 24) | (b[2] << 16) | (b[1] << 8) | b[0];
}

void setup() {  
  // put your setup code here, to run once:
  Serial.begin(9600);
  //mfrc522.PCD_Init(); //Init RFID reader
  pinMode(BUZZER_PIN, OUTPUT);

  Serial.write(0x30);
  // Setup rsa keys
  char buff[4]; // needs to be char cuz PySerial is fucking autistic and crashes if you send a null (0x00) byte and Arduino has no Serial.print() overload for uint8_t (don't ask me why, it's also kinda autistic). Maybe you can see I'm a bit mad but that's cuz I've been debugging this stupid interaction for an entire day and now at 21:07, finally realized the problem and now have to rewrite the entire codebase making it worse by converting every 32 bit integer into a 32 BYTE BINARY STRING AAAAAARGH
  while(Serial.available() < 4) ;
  size_t a = Serial.readBytes(buff, sizeof(buff));
  pyn = ui32_le(buff);
  memset(&buff, 0, sizeof(buff));

  while(Serial.available() < 4) ;
  Serial.readBytes(buff, sizeof(buff));
  privkey.d = ui32_le(buff);
  memset(&buff, 0, sizeof(buff));

  while(Serial.available() < 4) ;
  Serial.readBytes(buff, sizeof(buff));
  privkey.n = ui32_le(buff);
  memset(&buff, 0, sizeof(buff));
  
  Serial.write('0');

  SPI.begin();
  mfrc522.PCD_Init();

  tone(BUZZER_PIN, 1000);
  delay(100);
  tone(BUZZER_PIN, 1500);
  delay(200);
  noTone(BUZZER_PIN);
}

void loop() {
  while(!mfrc522.PICC_IsNewCardPresent()) ;

  // Select one of the cards
  while (!mfrc522.PICC_ReadCardSerial()) ;
  
  uint32_t uid = mfrc522.uid.uidByte[0];

  for(int i=1; i<4; i++) {
    uid = uid << 8;
    uid |= mfrc522.uid.uidByte[i];
  }
  
  mfrc522.PICC_HaltA();
  
  // Encrypt the uid with the Python public key, wich we don't do as the Arduino is way too slow
  //uint32_t cuid = modpow(uid, 65537, pyn);

  Serial.println(uid, BIN);
 

  while(Serial.available() <= 0) ;
  uint8_t status_code[1];
  Serial.readBytes(status_code, 1);
  switch(status_code[0]) {
    case 0: { // success
      // Read the new uid to write
      while(Serial.available() <= 0) ;
      uint8_t uidBuff[4];
      Serial.readBytes(uidBuff, sizeof(uidBuff));
      uint32_t uidToWrite = modpow(ui32_le(uidBuff), privkey.d, privkey.n);
      // TODO: actually write the tag

      tone(BUZZER_PIN, 1000);
      delay(100);
      tone(BUZZER_PIN, 1500);
      delay(200);
      noTone(BUZZER_PIN);
      break;
    }
    case 1: { // failure
      tone(BUZZER_PIN, 1500);
      delay(100);
      tone(BUZZER_PIN, 1000);
      delay(200);
      noTone(BUZZER_PIN);
      break;
    }
  }
  // TODO: make more auth code tones

}
