/** @file socketserver.c
 * 
 */
 
 
#include "jack-ring-socket-server.h"
 
void *connection_handler(void *socket_desc)
{
	//Get the socket descriptor
	int sock = *(int*)socket_desc;
	int readed;
	char client_data[4096];
	char out[256];
	while ((readed = recv(sock, client_data, sizeof(client_data),0)) > 0) {
            if (strncmp(client_data,"rate",4)==0){
                sprintf(out,"%d\n",MyRing.samplerate);
                write (sock, out, sizeof(out));            
            }
            if (strncmp(client_data,"len",3)==0){
                sprintf(out,"%d\n",MyRing.len);
                write (sock, out, sizeof(out));            
            }
            if (strncmp(client_data,"nframes",7)==0){
                sprintf(out,"%d\n",MyRing.nframes);
                write (sock, out, sizeof(out));            
            }
            if (strncmp(client_data,"seconds",7)==0){
                sprintf(out,"%d\n",MyRing.seconds);
                write (sock, out, sizeof(out));            
            }            
            if (strncmp(client_data,"dump",4)==0){
                ring_node *first,*current;
                first = current = MyRing.last;
    
                int i=0;
                printf ("Size of transission block: %ld\n", sizeof (jack_default_audio_sample_t) * MyRing.nframes * 2);
                do {
                    send(sock, current->data, sizeof (jack_default_audio_sample_t) * MyRing.nframes * 2, 0);
                    current = current -> next;        
                    i++;
                } while (current != first);
                printf ("Number of cycles: %d\n",i);
            }	
 	}
	
        if (readed == 0) {
		puts("Client disconnected");
		fflush(stdout);                   
        }
	
	//Free the socket pointer
	free(socket_desc);
	
	return 0;
}
