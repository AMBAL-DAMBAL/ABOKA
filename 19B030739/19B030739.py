import pygame as pg
from pygame.math import Vector2
from pygame import mixer
from random import randint

from threading import Thread
pg.init()
font = pg.font.SysFont('Times new roman', 32)

import pika
import uuid
import json

LOGIN = VPORT = 'dar-tanks'
PASSWORD = '5orPLExUYnyVYZg48caMpX'
IP = '34.254.177.17'
PORT = 5672

class RPC(object):
    def __init__(self):
        credentials = pika.PlainCredentials(LOGIN, PASSWORD)
        self.connection = pika.BlockingConnection(pika.ConnectionParameters(
            IP, PORT, VPORT, credentials))

        self.channel = self.connection.channel()

        result = self.channel.queue_declare(queue='', exclusive=True, auto_delete=True)
        self.callback_queue = result.method.queue

        self.channel.queue_bind(exchange='X:routing.topic',
                                queue=self.callback_queue)

        self.channel.basic_consume(
            queue=self.callback_queue,
            on_message_callback=self.on_response,
            auto_ack=True)

    def on_response(self, ch, method, props, body):
        if self.corr_id == props.correlation_id:
            self.response = json.loads(body)

            # TOKEN = json.loads(body['token'])

            # print("Received:  type: %r" % props.type)
            # print("           body: %r" % json.loads(body))

    def call(self, key, message={}):
        self.response = None
        self.corr_id = str(uuid.uuid4())
        self.channel.basic_publish(
            exchange='X:routing.topic',
            routing_key=key,
            properties=pika.BasicProperties(
                reply_to=self.callback_queue,
                correlation_id=self.corr_id,
            ),
            body=json.dumps(message))
        while self.response is None:
            self.connection.process_data_events()
        return self.response

class consumer_client(Thread):
    def __init__(self, room_id):
        super().__init__()
        credentials = pika.PlainCredentials(LOGIN, PASSWORD)
        self.connection = pika.BlockingConnection(pika.ConnectionParameters(
            IP, PORT, VPORT, credentials))

        self.channel = self.connection.channel()

        result = self.channel.queue_declare(queue='', exclusive=True, auto_delete=True)
        self.callback_queue = result.method.queue

        self.channel.queue_bind(
            exchange='X:routing.topic',
            queue=self.callback_queue,
            routing_key='event.state.' + room_id)

        self.channel.basic_consume(
            queue=self.callback_queue,
            on_message_callback=self.on_response,
            auto_ack=True)

        self.response = None
        # print("ok")
        # self.channel.start_consuming()
        # print("ok")

    def on_response(self, ch, method, props, body):
        self.response = json.loads(body)
        # print(self.response)

    def run(self):
        self.channel.start_consuming()

UP = 'UP'
DOWN = 'DOWN'
LEFT = 'LEFT'
RIGHT = 'RIGHT'

MOVE_KEYS = {
    pg.K_w: UP,
    pg.K_s: DOWN,
    pg.K_d: RIGHT,
    pg.K_a: LEFT
}

 

class multiplayer():

    def __init__(self):
        self.rpc = RPC()
        self.status()
        self.room = "room-27"
        self.event_client = consumer_client(self.room)
        self.event_client.start()
        self.font = pg.font.SysFont("Times new roman", 16)
        self.fps = 60
        self.done = False
        self.score = 0
        self.clock = pg.time.Clock()
        self.screen =  pg.display.set_mode((1000, 600))
        # self.screen = pg.Surface(self.sc.get_size())
        #self.panel = pg.display.set_mode((200,200))
        self.TOKEN = ''
        self.tankId = ''
        self.health = 3
    def draw_info(self, cnt, id, x, y, width, height, direction, health, score, **kwargs):
        center = (x + int(width / 2), y + int(height / 2))
        color = (160, 32, 240)
        if id == self.tankId:
            color = (0, 255, 255)
        tank_id = self.font.render(str(id), True, color)

        self.screen.blit(tank_id, ((820, cnt * 100), (width, height)))

        hp = self.font.render('HP:' + str(health), True, color)
        self.screen.blit(hp, ((820, cnt * 100 + 25), (width, height)))

        sc = self.font.render('SC:' + str(score), True, color)
        self.screen.blit(sc, ((820, cnt * 100 + 50), (width, height)))

    def draw_tank(self, id, x, y, width, height, direction, health, score, **kwargs):
        center = (x + int(width / 2), y + int(height / 2))
        color = (160, 32, 240)
        if id == self.tankId:
            color = (0, 255, 255)
            self.score = score
        tank_id =  self.font.render(str(id), True, color)
        self.screen.blit(tank_id, ((x, y - 20), (width, height)))

        tank_c = (x + int(width / 2), y + int(width / 2))
        pg.draw.rect(self.screen, color, (x, y, width, width), width // 20 + 5 // 2)
        pg.draw.circle(self.screen, color, tank_c, width // 3)
        if direction == "RIGHT":
            pg.draw.line(self.screen, color, tank_c,
                             (x + width + int(width / 2), y + int(width / 2)), 1  + 5 // 2)
        if direction == "LEFT":
            pg.draw.line(self.screen, color, tank_c, (x - int(width / 2), y + int(width / 2)),
                             1 + 5 // 2)
        if direction == "UP":
            pg.draw.line(self.screen, color, tank_c, (x + int(width / 2), y - int(width / 2)),
                             1 + 5 // 2)
        if direction == "DOWN":
            pg.draw.line(self.screen, color, tank_c,
                             (x + int(width / 2), y + width + int(width / 2)), 1  + 5 // 2)

    def draw_bullet(self, x, y, width, height, direction, owner, **kwargs):
        color = (160, 32, 240)
        if(owner == self.tankId):
            color = (0, 255, 255)
        pg.draw.rect(self.screen, color, (x, y, width, height), 1)

    def handle_events(self):
        for event in pg.event.get():
            if event.type == pg.QUIT:
                self.done = True
                self.rpc.connection.close()
            if event.type == pg.KEYDOWN:
                if event.key == pg.K_UP:
                    self.turn_tank("UP")
                if event.key == pg.K_DOWN:
                    self.turn_tank("DOWN")
                if event.key == pg.K_RIGHT:
                    self.turn_tank("RIGHT")
                if event.key == pg.K_LEFT:
                    self.turn_tank("LEFT")
                if event.key == pg.K_SPACE:
                    bulletSound = mixer.Sound("laser.wav")
                    bulletSound.play()
                    self.fire()
    def gameover(self):
        while not self.done:
            self.screen.fill((0, 0, 0))
            self.dt = self.clock.tick(self.fps) / 1000
            self.handle_events()
            self.font = pg.font.SysFont("Arial", 62)
            hp = self.font.render('GAME OVER', True, (255,255,255))
            self.screen.blit(hp, ((250, 200), (250, 200)))

            sc = self.font.render('Your score:' + str(self.score), True, (255,255,255))
            self.screen.blit(sc, ((250, 300), (250, 300)))
            pg.display.flip()

    def run(self):
        r = self.register()

        self.tankId = r["tankId"]
        print(self.tankId)
        while not self.done:
            self.screen.fill((0, 0, 0))
            self.dt = self.clock.tick(self.fps) / 1000

            hits = self.event_client.response["hits"]
            bullets = self.event_client.response["gameField"]["bullets"]
            winners = self.event_client.response["winners"]
            losers = self.event_client.response["losers"]
            tanks = self.event_client.response["gameField"]["tanks"]
            remaining_time = self.event_client.response["remainingTime"]
            if remaining_time == 0:
                self.gameover()
                break
            for tank in tanks:
                self.draw_tank(**tank)
            for bullet in bullets:
                self.draw_bullet(**bullet)
            ok = False
            for loser in losers:
                if self.tankId == loser["tankId"]:
                    self.gameover()
                    ok = True
                    break
            if ok:
                break

            pg.draw.rect(self.screen, (255,255,255), (800, 0, 200, 600))
            cnt = 0

            time = self.font.render("Remaining Time:" + str(remaining_time), True, (0, 0, 0))
            self.screen.blit(time, ((820, cnt * 100 + 25), (0, 0)))

            for tank in tanks:
                cnt += 1
                self.draw_info(cnt, **tank)

            self.handle_events()
            pg.display.flip()

    def register(self):
        message = {
            "roomId": self.room
        }
        r = self.rpc.call("tank.request.register", message)
        self.TOKEN = r["token"]
        return r

    def turn_tank(self, direction):
        message = {
            "token": self.TOKEN,
            "direction": direction
        }
        self.rpc.call("tank.request.turn", message)

    def status(self):
        r = self.rpc.call('tank.request.healthcheck')
        print(r)

    def fire(self):
        message = {
            "token": self.TOKEN,
        }
        self.rpc.call("tank.request.fire", message)

class Player(pg.sprite.Sprite):

    def __init__(self, pos, color, left, right, up, down, fire,
                 all_sprites, bullets, enemy_bullets):
        super().__init__()
        self.image = pg.Surface((30, 50))
        self.image.fill(color)
        self.rect = self.image.get_rect(topleft=pos)
        self.vel = Vector2(0, 0)
        self.pos = Vector2(self.rect.topleft)
        self.dt = 0.03
        self.key_left = left
        self.key_right = right
        self.key_up = up
        self.key_down = down
        self.key_fire = fire
        self.all_sprites = all_sprites
        self.bullets = bullets
        self.enemy_bullets = enemy_bullets
        self.fire_direction = Vector2(350, 0)
        self.health = 3

    def update(self, dt):
        self.dt = dt
        self.pos += self.vel
        self.rect.center = self.pos

        if self.pos.x<=0:
            self.pos.x=1000
        if self.pos.x >1000:
            self.pos.x=0
        if self.pos.y > 800:
            self.pos.y=0
        if self.pos.y <=0:
            self.pos.y=800


        collided_bullets = pg.sprite.spritecollide(self, self.enemy_bullets, True)
        for bullet in collided_bullets:
            self.health -= 1
            if self.health <= 0:
                self.kill()

    def handle_event(self, event):
        if event.type == pg.KEYDOWN:
            if event.key == self.key_left:
                self.vel.x = -90 * self.dt
                self.fire_direction = Vector2(-350, 0)
            elif event.key == self.key_right:
                self.vel.x = 90 * self.dt
                self.fire_direction = Vector2(350, 0)
            elif event.key == self.key_up:
                self.vel.y = -90 * self.dt
                self.fire_direction = Vector2(0, -350)
            elif event.key == self.key_down:
                self.vel.y = 90 * self.dt
                self.fire_direction = Vector2(0, 350)
            elif event.key == self.key_fire:   
                bullet = Bullet(self.rect.center, self.fire_direction)
                self.bullets.add(bullet)
                self.all_sprites.add(bullet)
         


class Bullet(pg.sprite.Sprite):

    def __init__(self, pos, velocity):
        super().__init__()
        self.image = pg.Surface((5, 5))
        self.image.fill(pg.Color('aquamarine1'))
        self.rect = self.image.get_rect(center=pos)
        self.pos = pos
        self.vel = velocity

    def update(self, dt):
        if self.pos.x <=0:
            self.pos.x=1000
        if self.pos.x >1000:
            self.pos.x=0
        if self.pos.y >800:
            self.pos.y=0
        if self.pos.y <=0:
            self.pos.y=800

        
        self.pos += self.vel * dt
        self.rect.center = self.pos


 
     

class Game:

    def __init__(self):
        self.fps = 30
        self.done = False
        self.clock = pg.time.Clock()
        self.screen = pg.display.set_mode((1000, 800))
        self.bg_color = pg.Color('gray30')

         
        self.all_sprites = pg.sprite.Group()
        self.bullets1 = pg.sprite.Group()    
        self.bullets2 = pg.sprite.Group()   
        player1 = Player(
            (100, 300), pg.Color('dodgerblue2'),
            pg.K_a, pg.K_d, pg.K_w, pg.K_s, pg.K_f,
            self.all_sprites, self.bullets1, self.bullets2)   
        player2 = Player(
            (300, 400),  pg.Color('sienna2'),
            pg.K_LEFT, pg.K_RIGHT, pg.K_UP, pg.K_DOWN, pg.K_SPACE,
            self.all_sprites, self.bullets2, self.bullets1)   
        self.all_sprites.add(player1, player2)
        self.players = pg.sprite.Group(player1, player2)
        
        
     def main_menu(self):
        while not self.donemenu:
            self.handle_events_menu()
            self.dt = self.clock.tick(self.fps) / 1000
            single = font.render('Single Player: press s' , True, (255, 123, 100))
            multi = font.render('Multiplayer: press m', True, (255, 125, 100))
             

            self.screen.fill(self.bg_color)

            self.screen.blit(multi, ((250, 150), (250, 150)))
            self.screen.blit(single, ((250, 100), (250, 100)))
             
            pg.display.flip()

    def run(self):
        while not self.done:
            self.dt = self.clock.tick(self.fps) / 1000
            self.handle_events()
            self.run_logic()
            self.draw()

    def handle_events(self):
        for event in pg.event.get():
            if event.type == pg.QUIT:
                self.done = True
            for player in self.players:
                player.handle_event(event)

    def run_logic(self):
        self.all_sprites.update(self.dt)

    def draw(self):
        self.screen.fill(self.bg_color)
        self.all_sprites.draw(self.screen)
        pg.display.flip()


if __name__ == '__main__':
    pg.init()
    Game().run()
    pg.quit()
