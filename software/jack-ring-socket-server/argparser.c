/** @file argparser.c
 * 
 */
 
 
#include "argparser.h"


const char *argp_program_version = "jack-ring-socket-server 1.0.0";
char doc[] = "record audio frames into a ringbuffer with tcp socket access";
const char *argp_program_bug_address = "rocco.demarco@irbim.cnr.it";
char args_doc[] = "";

error_t parse_opt(int key, char *arg, struct argp_state *state){

    struct arguments *arguments = state->input;
    switch(key){

        case 'p':
            arguments->port = atoi(arg);
            break;
        case 's':
            arguments->seconds = atoi(arg);
            break;
        case 'n':
            arguments->name = arg;
            break;

        default:
            return ARGP_ERR_UNKNOWN;
    }

    return 0;
}
