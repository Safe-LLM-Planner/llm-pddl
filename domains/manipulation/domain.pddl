(define (domain manipulation)
    (:requirements :strips :typing)
    
    (:types 
        location 
        object 
        electrical-object - object
    )

    (:predicates 
        (robot-at ?l - location)
        (at ?o - object ?l - location)
        (left-hand-empty)
        (right-hand-empty)
        (holding-left ?o - object)   ; Object held in left hand
        (holding-right ?o - object)  ; Object held in right hand
        (holding-both ?o - object)  ; Object held in right hand
        (plugged-in ?e - electrical-object)
    )

    (:action go-to
        :parameters (?from ?to - location)
        :precondition (and (robot-at ?from))
        :effect (and (robot-at ?to)
                     (not (robot-at ?from))
        )
    )

    (:action pick-left
        :parameters (?obj - object ?l - location)
        :precondition (and (at ?obj ?l) (robot-at ?l) (left-hand-empty))
        :effect (and (holding-left ?obj)         
                     (not (at ?obj ?l))
                     (not (left-hand-empty))
        )
    )

    (:action pick-right
        :parameters (?obj - object ?l - location)
        :precondition (and (at ?obj ?l) (robot-at ?l) (right-hand-empty))
        :effect (and (holding-right ?obj)        
                     (not (at ?obj ?l))
                     (not (right-hand-empty))
        )
    )

    (:action pick-both
        :parameters (?obj - object ?l - location)
        :precondition (and (at ?obj ?l) (robot-at ?l) (left-hand-empty) (right-hand-empty))
        :effect (and (holding-both ?obj)        
                     (not (at ?obj ?l))
                     (not (left-hand-empty))
                     (not (right-hand-empty))
        )
    )

    (:action place-left
        :parameters (?obj - object ?l - location)
        :precondition (and (holding-left ?obj) (robot-at ?l))
        :effect (and (at ?obj ?l)
                     (left-hand-empty)
                     (not (holding-left ?obj))
        )
    )

    (:action place-right
        :parameters (?obj - object ?l - location)
        :precondition (and (holding-right ?obj) (robot-at ?l))
        :effect (and (at ?obj ?l)
                     (right-hand-empty)
                     (not (holding-right ?obj))
        )
    )

    (:action place-both
        :parameters (?obj - object ?l - location)
        :precondition (and (holding-both ?obj) (robot-at ?l))
        :effect (and (at ?obj ?l)
                     (left-hand-empty)
                     (right-hand-empty)
                     (not (holding-both ?obj))
        )
    )

    (:action unplug
        :parameters (?e - electrical-object ?l - location)
        :precondition (and (at ?e ?l) (robot-at ?l) (plugged-in ?e))
        :effect (and (not (plugged-in ?e)))
    )
)
