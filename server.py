"""Triva bot server
Alan Marchiori
2019
"""

import socket
import select
import datetime
from trivia_game import TriviaClient, TriviaServer
import logging
import sys
def main(addr, game_port, web_port,
         q_rate = datetime.timedelta(seconds=10)):
    "main game entry point. everything is event driven."
    log = logging.getLogger()

    game_skt = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    #web_skt = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    web_skt = None
    game_skt.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
    #web_skt.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)

    game_skt.bind((addr, game_port))
    #web_skt.bind((addr, web_port))

    game_skt.listen()
    #web_skt.listen()

    game_skt.setblocking(False)
    #web_skt.setblocking(False)

    log.info("Game server running on {}".format((addr,game_port)))
    #log.info("Web server running on {}".format((addr,web_port)))

    # trivia game server
    ts = TriviaServer()

    # game and web client socket list
    g_cli = []
    w_cli = []
    games = {}

    next_question_time = datetime.datetime.now() + q_rate

    while True:
        try:
            r,w,e = select.select(
                #[game_skt, web_skt] + g_cli + w_cli,
                [game_skt] + g_cli + w_cli,
                [],
                g_cli + w_cli,
                1)

            for skt in e:
                log.info("Socket closed: {}".format(skt))
                # remove closed connections
                if skt in g_cli:
                    g_cli.remove(skt)
                if skt in w_cli:
                    w_cli.remove(skt)
                if skt in games:
                    del games[skt]
            if len(e) > 0:
                continue # reselect

            for skt in r:

                if skt in [game_skt, web_skt]:
                    if skt == game_skt:
                        cli, cli_addr = skt.accept()
                        cli.setblocking(False)
                        games[cli] = TriviaClient(cli)
                        g_cli.append(cli)
                    elif skt == web_skt:
                        cli, cli_addr = skt.accept()
                        cli.setblocking(False)
                        w_cli.append(cli)
                    else:
                        assert "Not possible."
                else:
                    try:
                        msg = skt.recv(4096)
                    except ConnectionResetError:
                        msg = ""
                    if len(msg)>0:
                        log.debug("reading from {}".format(skt.getpeername()))
                        if skt in g_cli:
                            games[skt].handle(msg)
                        elif skt in w_cli:
                            handle_ajax(skt.decode())
                        else:
                            log.error("unknown socket {}".format(skt))
                            exit(-99)
                    else:
                        try:
                            log.debug("disconnect from {}".format(skt.getpeername()))
                            skt.close()
                        except:
                            pass
                        if skt in g_cli:
                            g_cli.remove(skt)
                        if skt in w_cli:
                            w_cli.remove(skt)
                        if skt in games:
                            del games[skt]

            if datetime.datetime.now() > next_question_time:
                next_question_time = datetime.datetime.now() + q_rate
                question = ts.get_question()
                # log.info("New question: {}".format(question['question']))
                for skt, game in games.items():
                    game.send_question(question)

        except KeyboardInterrupt:
            print("Ctrl-c, quit!")
            break

if __name__ == "__main__":
    debug = True

    if debug:
        FORMAT = '%(asctime)-15s %(levelname)-6s: %(message)s'
        logging.basicConfig(filename='trivia.log', format=FORMAT, level=logging.DEBUG)
        logging.getLogger().addHandler(logging.StreamHandler(sys.stdout))

    main('0.0.0.0', 6997, 36997,q_rate = datetime.timedelta(seconds=15))
