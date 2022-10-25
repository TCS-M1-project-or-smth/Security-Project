/*
  RFID.cpp - Library for reading the UID of an RFID tag.
*/

#define SS_PIN 10
#define RST_PIN 9

#include "Arduino.h"
#include "RFID.h"

const byte UID_SIZE = 4;
MFRC522 mfrc522(SS_PIN, RST_PIN ); // unglobalize variable?

RFID::RFID() { // why create constructor, and still use global variables? cuz its static
}

void RFID::begin() {
  SPI.begin();
  mfrc522.PCD_Init();
}

uint32_t RFID::readUID() {
  uint32_t uid;
  while ( ! mfrc522.PICC_IsNewCardPresent());
  while ( ! mfrc522.PICC_ReadCardSerial());
  // UID is now in mfrc522.uid.uidbyte
  
  uid = mfrc522.uid.uidByte[0];

  for(int i=1; i<UID_SIZE; i++) {
    uid = uid << 8;
    uid |= mfrc522.uid.uidByte[i];
  }

  mfrc522.PICC_HaltA();
  
  return uid;
}