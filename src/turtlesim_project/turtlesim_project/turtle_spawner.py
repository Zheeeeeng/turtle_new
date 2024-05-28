#!/usr/bin/env python3
import random
import math
from functools import partial
import rclpy
from rclpy.node import Node
from turtlesim.srv import Spawn, Kill, SetPen
from std_srvs.srv import Empty
from robot_interfaces.msg import Turtle, TurtleArray
from robot_interfaces.srv import CatchTurtle

random.seed(75)

class TurtleSpawnerNode(Node): 
    def __init__(self):
        super().__init__("turtle_spawner")
        self.turtle_first_name_ = "turtle"
        self.turtle_counter = 1
        self.alive_turtles_ = []
        self.queue_turtles_ = []
        self.caught_turtle_ = None

        self.Hide_line("turtle1")
        self.alive_turtles_publisher_ = self.create_publisher(TurtleArray, "alive_turtles", 10)
        self.queue_turtles_publisher_ = self.create_publisher(TurtleArray, "queue_turtles", 10)
        
        # Change the frequency to 3 seconds
        self.spawn_frequency_ = self.declare_parameter("spawn_frequency", 3).value
        # Declare parameter for circular spawn
        self.circle_spawn_ = self.declare_parameter("circle_spawn", False).value
        self.timer_ = self.create_timer(self.spawn_frequency_, self.spawn_new_turtle)

        # Creating service /catch_turtle
        self.catch_turtle_service_ = self.create_service(CatchTurtle, "catch_turtle", self.callback_catch_turtle)
    
    # Hide the track line
    def Hide_line(self, turtle_name):
        cli = self.create_client(SetPen, f"{turtle_name}/set_pen")
        while not cli.wait_for_service(timeout_sec=1.0):
            self.get_logger().info('service not available, waiting again...')
        req = SetPen.Request()
        req.r, req.g, req.b, req.width, req.off = 220, 0, 0, 3, 1
        cli.call_async(req)

    # Service Callback
    def callback_catch_turtle(self, request, response):
        self.kill_turtle(request.turtle_name)
        response.success = True
        return response

    # Publish Functions
    def publish_alive_turtles(self):
        msg = TurtleArray()
        msg.turtles = self.alive_turtles_
        self.alive_turtles_publisher_.publish(msg)

    def publish_queue_turtles(self):
        msg = TurtleArray()
        msg.turtles = self.queue_turtles_
        self.queue_turtles_publisher_.publish(msg) 

    # Turtle Spawning
    def spawn_new_turtle(self):
        self.turtle_counter += 1
        name = f"{self.turtle_first_name_}{self.turtle_counter}"
        
        if self.circle_spawn_:
            positions = [(2.1, 2.1), (2.1, 8.9), (8.9, 8.9), (8.9, 2.1)]
            x, y = positions[(self.turtle_counter - 1) % 4]
        else:
            x, y = random.uniform(2.0, 9.0), random.uniform(2.0, 9.0)
            
        theta = random.uniform(0.0, 2 * math.pi)
        self.spawn_turtle(x, y, theta, name)

    # Service Calls
    # 1. Turtle Spawner
    def spawn_turtle(self, x, y, theta, name):
        client = self.create_client(Spawn, "spawn")
        while not client.wait_for_service(1.0):
            self.get_logger().warn("Waiting for Server...")
        request = Spawn.Request()
        request.x, request.y, request.theta, request.name = x, y, theta, name
        client.call_async(request).add_done_callback(partial(self.handle_spawn_response, x=x, y=y, theta=theta, name=name))

    def handle_spawn_response(self, future, x, y, theta, name):
        try:
            response = future.result()
            if response.name:
                self.get_logger().info(f"Turtle {response.name} has been spawned")
                new_turtle = Turtle(name=response.name, x=x, y=y, theta=theta)
                self.Hide_line(new_turtle.name)
                self.alive_turtles_.append(new_turtle)
                self.publish_alive_turtles()
        except Exception as e:
            self.get_logger().error(f"Service call failed: {e}")

    # 2. Turtle Killer
    def kill_turtle(self, name):
        for i, turtle in enumerate(self.alive_turtles_):
            if turtle.name == name:
                self.queue_turtles_.append(self.alive_turtles_.pop(i))
                self.publish_alive_turtles()
                self.publish_queue_turtles()
                break

def main(args=None):
    rclpy.init(args=args)
    node = TurtleSpawnerNode()
    rclpy.spin(node)
    rclpy.shutdown()

if __name__ == "__main__":
    main()