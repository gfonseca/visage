#include <Adafruit_NeoPixel.h>
#ifdef __AVR__
#include <avr/power.h> // Required for 16 MHz Adafruit Trinket
#endif
#include <ESP8266WiFi.h>
#include <WiFiUdp.h>


#define LED_PIN    2
#define LED_COUNT 46 
#define BUFF_SIZE 2000
#define SERVER_PORT 4210
#define NO_CLIENT_TIMEOUT 5000

const char* ssid = "Brain Damage";
const char* password = "scube7890";

typedef struct alarm_clock {
  int elapsed_time;
  int alarm_time;
} alarm_clock;

alarm_clock  alarm_no_server;
alarm_clock system_clocks[3];

unsigned int localUdpPort = SERVER_PORT;  // local port to listen on
int R, G, B;
int ledindex = 0;
int packetSize;
char msg_buffer[BUFF_SIZE];
unsigned long int old_time, current_time;
int delta_time;
int server_status = false;


WiFiUDP Udp;
Adafruit_NeoPixel strip(LED_COUNT, LED_PIN, NEO_GRB + NEO_KHZ800);


// ## SETUP ##
void setup()
{
  Serial.begin(115200);
 
  Serial.printf("Connecting to %s ", ssid);
  WiFi.begin(ssid, password);
  while (WiFi.status() != WL_CONNECTED) {
    delay(500);
    Serial.print(".");
  }
  
  Serial.println(" connected");

  Udp.begin(localUdpPort);
  Serial.printf("Now listening at IP %s, UDP port %d\n", WiFi.localIP().toString().c_str(), localUdpPort);

  //LED STRIP
  strip.begin();
  strip.setBrightness(180);

  
  alarm_no_server = *new_alarm_clock(NO_CLIENT_TIMEOUT);
  system_clocks[0] = alarm_no_server;
  alarm_no_server.elapsed_time = NO_CLIENT_TIMEOUT;
}

// ## LOOP ##
void loop() {

  // ## OK FOR PACKET RECEIVED ##
  packetSize = Udp.parsePacket();
  if (packetSize) {
    if(!server_status) { 
      send_hello_message();
    }

    // ## LOAD CLIENT PACKET ##
    memset(msg_buffer, 0, BUFF_SIZE );
    Udp.read(msg_buffer, packetSize);
    
    // ## DRAW PIXELS ##
    draw_pixels(msg_buffer);

    // ## SET SERVER INACTIVITY FOR ZERO ##
    zero_clock(&alarm_no_server);

    // ## RESPOND TO CLIENT AFTER A PACKET ##
    server_status = true;

    return;
  }

  // ## CHECK FOR CLIENT ACTIVITY ##
  if (!server_status || check_alarm(alarm_no_server)) {
        no_server_effect();
        server_status = false;
        return;
  }
  // ## UPDATE ALARM CLOCKS WITH DELTA TIME##
  update_clocks(system_clocks, get_delta());
}

void send_hello_message() { 
  Udp.beginPacket(Udp.remoteIP(), 4211);
  Udp.write("vsg");
  Udp.write((char)10);
  Udp.write( (byte) (LED_COUNT & 0xFF) );
  Udp.write( (byte) ((LED_COUNT >> 8) & 0xFF));
  Udp.endPacket();
}

void no_server_effect() {
  char t = millis() >> 3;
    
  float factor = (((float)(t)*100.)/255.)/100.;
  char r = (char)(50. * factor);
  char g = 0;
  char b = (char)(90. * factor);  

  for (int i = 0; i <= LED_COUNT; i++){
    strip.setPixelColor(i, strip.Color(r, g, b));
  }
  strip.show();
}

int get_delta() {
   old_time = current_time;
   current_time = millis();
   return current_time - old_time;
}

void draw_pixels(char *msg_buffer) {
  ledindex = 0;
  for (int i = 0; i <= (LED_COUNT*3); i += 3){
    R = msg_buffer[i];
    G = msg_buffer[i+1];
    B = msg_buffer[i+2];
    //Serial.printf("%d, %d, %d\n", R, G, B);
    strip.setPixelColor(ledindex, strip.Color(R, G, B));
    ledindex++;
   }
   strip.show();  
}

void zero_clock(alarm_clock *ac) {
  ac->elapsed_time = 0;
}

void update_clocks(alarm_clock *clocks, int dt){
  for( int i = 0; i < sizeof(clocks); i++){
    clocks->elapsed_time += dt;
    clocks++;
  }
}

alarm_clock *new_alarm_clock(int alarm_time) {
  alarm_clock *ac = (alarm_clock*)malloc(sizeof(alarm_clock));
  ac->alarm_time = alarm_time;
  ac->elapsed_time = 0;
  return ac;
}

bool check_alarm(alarm_clock ac) {
//  Serial.printf("ac.elapsed_time: %d, ac.alarm_time %d, boom: %d\n", ac.elapsed_time, ac.alarm_time, ac.elapsed_time >= ac.alarm_time);
  return ac.elapsed_time >= ac.alarm_time;
}

void paint_black(int pixel_count) {
  strip.clear();
  for(int i=0; i<pixel_count; i++) {
    Serial.printf("%d, \n");
    strip.setPixelColor(i, strip.Color(0, 0, 0));
    strip.show();
  }
}