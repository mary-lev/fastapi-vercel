from anytree import Node


# Test case for the function
def test_minimax(node, max_depth, player_a_moves, expected):
    result = minimax(node, max_depth, player_a_moves)
    if expected == result:
        return True
    else:
        return False


# Code of the function
def minimax(node, max_depth, player_a_moves):
    if max_depth == 0 or len(node.children) == 0:
        return get_value(node)
    else:
        move_values = []
        for move in get_next_valid_moves(node):
            move_values.append(minimax(move, max_depth - 1, not player_a_moves))

        if player_a_moves:
            return max(move_values)
        else:
            return min(move_values)


# Ancillary functions for granted
def get_value(node):
    d = {"Move X": 2, "Move Y": 7, "Move Z": 5, "Move W": 10, "Move V": 8}
    return d[node.name]


def get_next_valid_moves(node):
    return node.children


# Tests
root = Node("Move Y")
node_1_1 = Node("Move X", root)
node_1_2 = Node("Move Y", root)
node_2_1 = Node("Move X", node_1_1)
node_2_2 = Node("Move Y", node_1_1)
node_2_3 = Node("Move Z", node_1_1)
node_2_4 = Node("Move W", node_1_2)
node_2_5 = Node("Move Y", node_1_2)
node_3_1 = Node("Move Y", node_2_2)
node_3_2 = Node("Move V", node_2_2)

print(test_minimax(root, 0, True, 7))
print(test_minimax(root, 2, True, 7))
print(test_minimax(root, 3, True, 7))
print(test_minimax(root, 7, True, 7))
