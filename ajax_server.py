"""Triva bot server
Alan Marchiori
2019
"""

import socket
import datetime
import logging
import select
import os
import json

import time

def send_stat(skt, user_path='./user_dat', logfile='trivia.log'):

    head = """HTTP/1.0 200 OK
Access-Control-Allow-Origin: *
Content-type: text/plain

"""

    body = "hi"

    lines = []

    for user in os.listdir(user_path):
        ufile = os.path.join(user_path, user)
        for tries in range(10):
            try:
                with open(ufile, 'r') as f:
                    udat = json.load(f)
            except:
                time.sleep(0.001)
                continue
            if 'counters' in udat:
                c = udat['counters']
                lines.append(
                    (
                        udat['score'],
                        "{:20s} {:10d} {:10d} {:10d} {:10d} {:10.2f}".format(
                            user,
                            c[0],
                            c[1],
                            c[2],
                            c[3],
                            udat['score'])
                    )
                )
            break

    lines = sorted(lines, key=lambda x:x[0], reverse=True)
    lines = [x[1] for x in lines]

    lines.insert(0,"-"*75)
    lines.insert(0,"{:<20} {:>10} {:>10} {:>10} {:>10} {:>10}".format(
        "USER",
        "CONNECTS",
        "CORRECT",
        "INCORRECT",
        "INVALID",
        "SCORE"
            ))
    lines.insert(0, "Generated at " + str(datetime.datetime.now()) + "\n")
    body = "\n".join(lines)

    for tries in range(10):
        try:
            with open(logfile,'r') as f:
                fsize = os.stat(logfile).st_size
                if fsize > 2048:
                    f.seek(fsize-2048)
                l = f.readlines()
                body += "\n"+ "-"*75 + "\n\nServer log:\n" + "".join(l[1:])
                break
        except:
            time.sleep(0.001)
            pass
    skt.send((head+body).encode())

def main(addr, port):
    log = logging.getLogger()
    web_skt = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    web_skt.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
    web_skt.bind((addr, port))
    web_skt.listen()
    web_skt.setblocking(False)
    log.info("AJAX server running on {}".format((addr,port)))

    cli = []
    while True:
        try:
            r,w,e = select.select(
                [web_skt] + cli,
                [],
                cli)
            for skt in r:
                if skt == web_skt:
                    cli_skt, cli_addr = skt.accept()
                    log.info("connect from {}".format(cli_addr))
                    cli_skt.setblocking(False)
                    cli.append(cli_skt)
                else:
                    m = skt.recv(4096)
                    if len(m) > 0:
                        log.info("{} rx << {}".format(
                            skt.getpeername(),
                            m.decode().split('\n')[0]))
                        send_stat(skt)
                        skt.close()
                    cli.remove(skt)


        except KeyboardInterrupt:
            log.info("Gootbye")
            break

if __name__ == "__main__":
    debug = True

    if debug:
        FORMAT = '%(asctime)-15s %(levelname)-6s: %(message)s'
        logging.basicConfig(format=FORMAT, level=logging.DEBUG)


    main('0.0.0.0', 36999)
