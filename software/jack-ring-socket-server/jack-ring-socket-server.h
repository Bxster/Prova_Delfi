/** @file jack-ring-socket-server.h
 * 
 * called by: main.c
 *
 * calls: ringbuffer.h socketserver.h jackclient.h 
 *
 */


#include <stdio.h>
#include <errno.h>
#include <unistd.h>
#include <stdlib.h>
#include <string.h>
#include <sys/socket.h>
#include <arpa/inet.h>
#include <jack/jack.h>
#include <argp.h>


#include "jackclient.h"
#include "ringbuffer.h"
#include "socketserver.h"
#include "argparser.h"


#ifndef GLOBALS
#define GLOBALS
extern sample_ring MyRing;
extern jack_port_t *input_port_left;
extern jack_port_t *input_port_right;
extern jack_port_t *output_port;
extern jack_client_t *client;
extern char doc[];
extern char args_doc[];
#endif
