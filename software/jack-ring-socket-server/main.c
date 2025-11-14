/** @file main.c
 * 
 */



#include "jack-ring-socket-server.h"
#include "jackclient.h"
#include "ringbuffer.h"
#include "socketserver.h"
#include "argparser.h"


// initialize the ring structure as global variable 
sample_ring MyRing;

// inizialize jack-client environment
jack_port_t *input_port_left;
jack_port_t *input_port_right;
jack_port_t *output_port;
jack_client_t *client;

static struct argp argp = {options, parse_opt, args_doc, doc};

int main (int argc, char *argv[]) {
	const char **ports;
	const char *server_name = NULL;
	jack_options_t options = JackNullOption;
	jack_status_t status;
	
	// create a new struct to hold arguments.
        struct arguments arguments;

        // set the default values for all of the args.
        arguments.name="RingServer";
        arguments.port=8888;
        arguments.seconds=2;
        // parse the cli arguments.so	
        argp_parse(&argp, argc, argv, 0, 0, &arguments);


	/* open a client connection to the JACK server */

	client = jack_client_open (arguments.name, options, &status, server_name);
	if (client == NULL) {
		fprintf (stderr, "jack_client_open() failed, "
			 "status = 0x%2.0x\n", status);
		if (status & JackServerFailed) {
			fprintf (stderr, "Unable to connect to JACK server\n");
		}
		exit (1);
	}
	if (status & JackServerStarted) {
		fprintf (stderr, "JACK server started\n");
	}
	if (status & JackNameNotUnique) {
		fprintf (stderr, "unique name `%s' assigned\n", jack_get_client_name(client));
	}

	// inizializzo struttura dati
	int nelements = jack_get_sample_rate(client) / jack_get_buffer_size(client) * arguments.seconds;  // manca n seconds!
	create_sample_ring(&MyRing, nelements, jack_get_sample_rate (client), jack_get_buffer_size(client), arguments.seconds);
	ring_debug(&MyRing);
	/* tell the JACK server to call `process()' whenever
	   there is work to be done.
	*/

	jack_set_process_callback (client, process, 0);

	/* tell the JACK server to call `jack_shutdown()' if
	   it ever shuts down, either entirely, or if it
	   just decides to stop calling us.
	*/

	jack_on_shutdown (client, jack_shutdown, 0);

	// Registrazione delle porte di ingresso
        input_port_left = jack_port_register(client, "input_left",
                                          JACK_DEFAULT_AUDIO_TYPE,
                                              JackPortIsInput, 0);

        input_port_right = jack_port_register(client, "input_right",
                                            JACK_DEFAULT_AUDIO_TYPE,
                                                JackPortIsInput, 0);

	if (input_port_left == NULL || input_port_right == NULL) {
        fprintf(stderr, "no more JACK ports available\n");
        exit(1);
    }

	/* Tell the JACK server that we are ready to roll.  Our
	 * process() callback will start running now. */

	if (jack_activate (client)) {
		fprintf (stderr, "cannot activate client");
		exit (1);
	}

	/* Connect the ports.  You can't do this before the client is
	 * activated, because we can't make connections to clients
	 * that aren't running.  Note the confusing (but necessary)
	 * orientation of the driver backend ports: playback ports are
	 * "input" to the backend, and capture ports are "output" from
	 * it.
	 */

	ports = jack_get_ports (client, NULL, NULL,
							JackPortIsPhysical|JackPortIsOutput);

	if (ports == NULL) {
		fprintf(stderr, "no physical capture ports\n");
		exit (1);
	}

	if (jack_connect(client, ports[0], jack_port_name(input_port_left))) {
        fprintf(stderr, "cannot connect left input port\n");
    }

    if (jack_connect(client, ports[1], jack_port_name(input_port_right))) {
        fprintf(stderr, "cannot connect right input port\n");
    }


	free (ports);

	/* keep running until stopped by the user */

	//sleep (-1);


        // gestione socket
        
	int socket_desc , new_socket , c , *new_sock;
	struct sockaddr_in server , socket_client;
	char *message;
	
	//Create socket
	socket_desc = socket(AF_INET , SOCK_STREAM , 0);
	if (socket_desc == -1)
	{
		printf("Could not create socket");
	}
	
	//Prepare the sockaddr_in structure
	server.sin_family = AF_INET;
	server.sin_addr.s_addr = INADDR_ANY;
	server.sin_port = htons( arguments.port );
	
	//Bind
	if( bind(socket_desc,(struct sockaddr *)&server , sizeof(server)) < 0)
	{
                printf("bind fail %s\n", strerror(errno));
		puts("bind failed");
		return 1;
	}
	puts("bind done");
	
	//Listen
	listen(socket_desc , 3);
	
	//Accept and incoming connection
	puts("Waiting for incoming connections...");
	c = sizeof(struct sockaddr_in);
	while( (new_socket = accept(socket_desc, (struct sockaddr *)&socket_client, (socklen_t*)&c)) )
	{
		puts("Connection accepted");
		
	        pthread_t sniffer_thread;
		new_sock = malloc(1);
		*new_sock = new_socket;
		
		if( pthread_create( &sniffer_thread , NULL ,  connection_handler , (void*) new_sock) < 0)
		{
			perror("could not create thread");
			return 1;
		}
		
		puts("Handler assigned");
	}        
        
        
       // fine gestione socket

	/* this is never reached but if the program
	   had some other way to exit besides being killed,
	   they would be important to call.
	*/

	jack_client_close (client);
	exit (0);
}
