/** @file ringbuffer.c
 * 
 *  This ringbuffer is designed to be filled (almost) in realtime by the jack_client process
 *  the aim of this data structure is to store the last ``n`` seconds of recording in every moment
 *  so, once filled for the first time, every incoming block to be stored will overwrite the oldest one
 * 
 */
#include <stdio.h> 
#include <stdlib.h>
#include <string.h>
#include "ringbuffer.h"

/** function create_sample_ring
 *     create and initialize the ring structure
 *
 * Input values:
 *     sample_ring *ring: a pointer to the global defined ring structure
 *     int nelements: how many frame blocks will be stored in the ring
 *     jack_nframes_t samplerate: samplerate returned from jack-server
 *     jack_nframes_t nframes: the number of frames contained in each block
 *     int seconds: the lenght of stored audio data in seconds
 *
 * returns:
 *     1 in case of success
 *     -1 otherwise 
 */
int create_sample_ring(sample_ring *ring, int nelements, jack_nframes_t samplerate, jack_nframes_t nframes, int seconds){
    // Populate ring structure with given values
    ring->len = nelements;
    ring->nframes = nframes;
    ring->samplerate = samplerate;
    ring->seconds = seconds;
    // defining 3 ring element pointers
    ring_node *first,*current,*new;
    // a pointer to the audio data block
    jack_default_audio_sample_t *data;
    
    // the ring have a number of nelements ring_nodes, each of these connected with the next one
    // the last one will be connected with the first    
    int i;
    for (i=0; i<nelements; i++) {
        // allocate memory to store the sample.
        data = (jack_default_audio_sample_t *) malloc(sizeof (jack_default_audio_sample_t) * nframes * 2);
        if (data == NULL){
            printf("ERRORE nell'allocazione\n\n");
            return -1;
        }
        // add a new ring_node...
        if (i == 0) {
             // this is the first one...   
             first =  malloc(sizeof(ring_node));
             current = first;
        } else {
             new =  malloc(sizeof(ring_node));
             current->next = new;
             current = new;
        }
        current->data = data;
    }
    // closing the ring...
    current->next = first;
    ring->last = first;
    return 1;
}



/** function ring_debug
 *     print the ring structure, showing pointers
 *
 * Input values:
 *     sample_ring *ring: a pointer to the global defined ring structure
 *
 * returs:
 *     nothing
 */
int ring_debug(sample_ring *ring){
    ring_node *first,*current;
    printf ("*** Ring buffer debug\nRing len:\t%d\nnFrames:\t%d\nSamplerate:\t%d\nSeconds:\t%d\nLast ptr:\t%p\n\n",
            ring->len, ring->nframes, ring->samplerate, ring->seconds, ring->last);
    first = current = ring->last;
    printf ("First element in the ringbuffer: [%p]\n",first);
    printf ("Nodes structure:\nElement\tNode addr\tNext ptr\tData addr\n");    
    int i=0;
    do {
        printf ("%d\t%p\t%p\t%p\n",i,current,current->next,current->data);
        i++;
        current = current -> next;        
    } while (current != first);
    return 1;
}

/** function add_to_ring
 *     add an frames block in the first available node (overwriting if already filled)
 *     and update the ring->last to the next node
 *     
 * Input values:
 *     sample_ring *ring: a pointer to the global defined ring structure
 *     jack_default_audio_sample_t *data: the audio data passed by jack-client process
 *
 * returs:
 *     nothing
 */
int add_to_ring(sample_ring *ring, jack_default_audio_sample_t *data){
     ring_node *current;
     current = ring->last;
     memcpy (current->data, data, sizeof (jack_default_audio_sample_t) * ring->nframes * 2);
     ring->last = current->next;
     return 1;     
}
