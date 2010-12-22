var Dom = YAHOO.util.Dom;
var Event = YAHOO.util.Event;
var $ = function(id) {
    return document.getElementById(id);
} 

//++++++++++++++++++++++++++++++++++++
// YUI ACCORDION
// 1/22/2008 - Edwart Visser
//
// accordion
//
// REQUIRES: yahoo-dom-event.js
//++++++++++++++++++++++++++++++++++++

YAHOO.namespace("lutsr");

YAHOO.lutsr.accordion = {
    properties : {
        multipleOpen : false
    },

    init : function(multipleOpen) {
        if(multipleOpen) {
            this.multipleOpen = multipleOpen;
        }

        var accordionObjects = Dom.getElementsByClassName("accordion");

        if(accordionObjects.length > 0) {
    
            for(var i=0; i<accordionObjects.length; i++) {
                if(accordionObjects[i].nodeName == "DL") {
                    var headers = accordionObjects[i].getElementsByTagName("dt");
                    var bodies = accordionObjects[i].getElementsByTagName("dd");
                }
                this.attachEvents(headers,i);
            }
        }
    },

    attachEvents : function(headers,nr) {
        for(var i=0; i<headers.length; i++) {
            var headerProperties = {
                objRef : headers[i],
                nr : i,
                jsObj : this
            }
            
            Event.addListener(headers[i].getElementsByTagName("span"),
                              "click", 
                              this.clickHeader,headerProperties);
            Event.addListener(headers[i].getElementsByTagName("input"),
                              "click",
                              this.clickHeaderCheckbox,headerProperties);
        }
    },
    
    clickHeader : function(e,headerProperties) {
        var parentObj = headerProperties.objRef.parentNode.parentNode;
        var headers = parentObj.getElementsByTagName("dd"); 
        var header = headers[headerProperties.nr];
    
        if(Dom.hasClass(header,"open")) {
            headerProperties.jsObj.collapse(header);
        } else {
            if(headerProperties.jsObj.properties.multipleOpen) {
                headerProperties.jsObj.expand(header);
            } else {
                for(var i=0; i<headers.length; i++) {
                    if(Dom.hasClass(headers[i],"open")) {
                        headerProperties.jsObj.collapse(headers[i]);
                    }
                }
                headerProperties.jsObj.expand(header);
            }
        }
    },

    clickHeaderCheckbox : function(e,headerProperties) {
        var objRef = headerProperties.objRef
        var headerCheck = objRef.getElementsByTagName("input")[0];
        var parentObj = objRef.parentNode.parentNode;
        var headers = parentObj.parentNode.getElementsByTagName("dd");
        var header = headers[headerProperties.nr];
        var checks = header.getElementsByTagName("input");
        
        for(var i=0; i<checks.length; i++) {
            if (checks[i].type!='checkbox') continue;
            if (checks[i].disabled) continue;
            checks[i].checked=headerCheck.checked;
        }
    },

    collapse : function(header) {
        Dom.removeClass(Dom.getPreviousSibling(header),"selected");
        Dom.removeClass(header,"open");
    },

    expand : function(header) {
        Dom.addClass(Dom.getPreviousSibling(header),"selected");
        Dom.addClass(header,"open");
    }
}

initPage = function() {
    YAHOO.lutsr.accordion.init();
}

Event.on(window,"load",initPage);
