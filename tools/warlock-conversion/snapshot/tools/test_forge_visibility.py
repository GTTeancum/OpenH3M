import unittest
from forge_visibility_partition import preserve_clusters


class VisibilityPartitionTests(unittest.TestCase):
    def test_removed_faces_keep_distinct_visibility_clusters(self):
        nodes = [(0, -2147483648, 1), (1, -2147483647, -2147483646)]
        selected, leaves, children, aliases = preserve_clusters(
            nodes, [True, False], [True, False, False], [0, 1, 2])
        self.assertEqual(selected, [0, 1])
        self.assertEqual(leaves, [0, 1, 2])
        self.assertEqual(children[1], (-2147483647, -2147483646))
        self.assertEqual(aliases, {1: 1, 2: 2})

    def test_only_discarded_collision_subtree_can_open_solid(self):
        nodes = [(0, -2147483648, 1), (1, -1, -2147483647)]
        selected, leaves, children, aliases = preserve_clusters(
            nodes, [True, False], [True, False], [0, 1])
        self.assertEqual(selected, [0])
        self.assertEqual(children[0], (-2147483648, -2147483647))
        self.assertEqual(leaves, [0, 1])
        selected, _, children, _ = preserve_clusters(
            nodes, [True, True], [True, True], [0, 1])
        self.assertEqual(selected, [0, 1])
        self.assertEqual(children[1][0], -1)

    def test_equivalent_empty_leaves_share_one_cluster_leaf(self):
        nodes = [(0, -2147483648, 1), (1, -2147483647, -2147483646)]
        selected, leaves, children, aliases = preserve_clusters(
            nodes, [True, False], [True, False, False], [0, 1, 1])
        self.assertEqual(selected, [0])
        self.assertEqual(leaves, [0, 1])
        self.assertEqual(aliases, {1: 1, 2: 1})


if __name__ == '__main__':
    unittest.main()
