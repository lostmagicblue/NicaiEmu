#!/usr/bin/env python3
"""Expose existing Emscripten input callbacks without changing the WASM ABI."""
import argparse
from pathlib import Path

def patch(text):
    marker = "/* magicblue-native-input-v2 */"
    if marker in text:
        raise ValueError("input bridge already present")
    anchor = "var registerKeyEventCallback="
    if text.count(anchor) != 1:
        raise ValueError("Emscripten keyboard callback shape changed; inspect generated JS")
    bridge = '''/* magicblue-native-input-v2 */
function magicbluePoint(x,y,target){var rect=target.getBoundingClientRect?target.getBoundingClientRect():{left:0,top:0,width:0,height:0};if(typeof window!=="undefined"&&window.EmuViewport&&window.EmuViewport.angle===90&&target===Module.canvas&&rect.width&&rect.height)return{x:(y-rect.top)/rect.height*target.clientWidth,y:(1-(x-rect.left)/rect.width)*target.clientHeight};return{x:x-(rect.left|0),y:y-(rect.top|0)}}
Module.magicblueAudioState=function(){return Object.keys(AL.contexts).map(function(id){var c=AL.contexts[id].audioCtx;return{state:c.state,time:c.currentTime,sampleRate:c.sampleRate}})};
Module.magicblueResumeAudio=function(){return Promise.all(Object.keys(AL.contexts).map(function(id){var c=AL.contexts[id].audioCtx;return c.state==="suspended"?c.resume():Promise.resolve()}))};
Module.magicblueKey=function(code,key,keyCode,down){var type=down?"keydown":"keyup",h=JSEvents.eventHandlers.find(function(h){return h.eventTypeString===type&&h.target===window})||JSEvents.eventHandlers.find(function(h){return h.eventTypeString===type});if(!h)return false;h.eventListenerFunc({timeStamp:performance.now(),location:0,ctrlKey:false,shiftKey:false,altKey:false,metaKey:false,repeat:false,charCode:0,keyCode:keyCode,which:keyCode,key:key,code:code,char:"",locale:"",preventDefault:function(){}});return true};
'''
    text = text.replace(anchor, bridge + anchor)
    old = 'HEAP32[idx+10]=e.clientX-(rect.left|0);HEAP32[idx+11]=e.clientY-(rect.top|0)'
    new = 'var mbPoint=magicbluePoint(e.clientX,e.clientY,target);HEAP32[idx+10]=mbPoint.x;HEAP32[idx+11]=mbPoint.y'
    if text.count(old) != 1:
        raise ValueError("Emscripten mouse event shape changed")
    text = text.replace(old, new)
    old = 'HEAP32[idx32+8]=t.clientX-(targetRect.left|0);HEAP32[idx32+9]=t.clientY-(targetRect.top|0)'
    new = 'var mbTouch=magicbluePoint(t.clientX,t.clientY,target);HEAP32[idx32+8]=mbTouch.x;HEAP32[idx32+9]=mbTouch.y'
    if text.count(old) != 1:
        raise ValueError("Emscripten touch event shape changed")
    return text.replace(old, new)

if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('javascript', type=Path)
    args = parser.parse_args()
    original = args.javascript.read_text(encoding='utf-8')
    args.javascript.write_text(patch(original), encoding='utf-8', newline='\n')
    print('Patched native keyboard and rotated pointer bridge:', args.javascript)
