/** @file argparser.h
 * 
 */
 
#include<stdlib.h>
#include <argp.h>
	
error_t parse_opt(int, char *, struct argp_state *);



#ifndef ARGPARSER
#define ARGPARSER

static struct argp_option options[] = {
    {"name", 'n', "name", 0, "jack-client name"},
    {"port", 'p', "port", 0, "daemon tcp port"},
    {"seconds", 's', "seconds", 0, "seconds to store in the ringbuffer"},
    {0}
};


struct arguments{
    int  port;
    int  seconds;
    char *name;
};

#endif
