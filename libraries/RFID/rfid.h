/*
  RFID.h - Library for reading the UID of an RFID tag.
*/

#ifndef RFID_h
#define RFID_h

#include <Arduino.h>
#include <..\MFRC522\MFRC522.h>
#include <SPI.h> // double include (MFRC522.h includes SPI.h)

class RFID // class structure is not needed, (yet?) redefine to namespace?
{
  public:
    RFID();
	void begin();
    uint32_t readUID();
};

#endif