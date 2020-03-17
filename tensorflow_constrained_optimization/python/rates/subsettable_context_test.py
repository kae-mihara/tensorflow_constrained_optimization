# Copyright 2018 The TensorFlow Constrained Optimization Authors. All Rights
# Reserved.
#
# Licensed under the Apache License, Version 2.0 (the "License"); you may not
# use this file except in compliance with the License. You may obtain a copy of
# the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS, WITHOUT
# WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied. See the
# License for the specific language governing permissions and limitations under
# the License.
# ==============================================================================
"""Tests for subsettable_context.py."""

from __future__ import absolute_import
from __future__ import division
from __future__ import print_function

import numpy as np
import tensorflow as tf

from tensorflow_constrained_optimization.python import graph_and_eager_test_case
from tensorflow_constrained_optimization.python.rates import defaults
from tensorflow_constrained_optimization.python.rates import subsettable_context
# Placeholder for internal import.


def create_contexts():
  """Returns a pair of `SubsettableContext`s to use in tests.

  We'll refer to the two contexts as "context1" and "context2". Both are subsets
  of the same parent context, which has:
    penalty_predicate    = [1, 0, 1, 0, 1, 0, 1, 0, 1, 0]
    constraint_predicate = [0, 1, 0, 1, 0, 1, 0, 1, 0, 1]
  context1 is subsetted from the parent context using:
    penalty_predicate1    = [0, 0, 1, 1, 1, 1, 0, 0, 0, 0]
    constraint_predicate1 = [1, 1, 0, 0, 0, 0, 1, 1, 1, 1]
  while context2 is subsetted deom the parent context using:
    penalty_predicate2    = [0, 0, 0, 0, 1, 1, 1, 1, 0, 0]
    constraint_predicate2 = [1, 1, 1, 1, 0, 0, 0, 0, 1, 1]

  Returns:
    The pair (context1, context2).
  """
  predictions = tf.constant(0.0, dtype=tf.float32, shape=(1,))
  # The predictions are passed as a lambda to support eager mode (in graph mode,
  # either a Tensor or a function are fine, but in eager mode, the predictions
  # *must* be a function).
  context = subsettable_context.rate_context(lambda: predictions)

  penalty_predicate = [
      True, False, True, False, True, False, True, False, True, False
  ],
  constraint_predicate = [
      False, True, False, True, False, True, False, True, False, True
  ],

  context = context.subset(penalty_predicate, constraint_predicate)

  penalty_predicate1 = [
      False, False, True, True, True, True, False, False, False, False
  ],
  constraint_predicate1 = [
      True, True, False, False, False, False, True, True, True, True
  ],

  penalty_predicate2 = [
      False, False, False, False, True, True, True, True, False, False
  ],
  constraint_predicate2 = [
      True, True, True, True, False, False, False, False, True, True
  ],

  context1 = context.subset(penalty_predicate1, constraint_predicate1)
  context2 = context.subset(penalty_predicate2, constraint_predicate2)

  return context1, context2


# @run_all_tests_in_graph_and_eager_modes
class SubsettableContextTest(graph_and_eager_test_case.GraphAndEagerTestCase):
  """Tests for `SubsettableContext` class."""

  def test_subset_of_subset(self):
    """Tests that taking the subset-of-a-subset works correctly."""
    context1, context2 = create_contexts()
    structure_memoizer = {
        defaults.DENOMINATOR_LOWER_BOUND_KEY: 0.0,
        defaults.GLOBAL_STEP_KEY: tf.compat.v2.Variable(0, dtype=tf.int32)
    }

    with self.wrapped_session() as session:
      # Make sure that the subset of a subset ANDs the conditions together in
      # condition1.
      expected_penalty_predicate = np.array([0, 0, 1, 0, 1, 0, 0, 0, 0, 0],
                                            dtype=np.float32)
      expected_constraint_predicate = np.array([0, 1, 0, 0, 0, 0, 0, 1, 0, 1],
                                               dtype=np.float32)
      self.assertAllEqual(
          expected_penalty_predicate,
          session.run(context1.penalty_predicate.tensor(structure_memoizer)))
      self.assertAllEqual(
          expected_constraint_predicate,
          session.run(context1.constraint_predicate.tensor(structure_memoizer)))
      # Likewise in condition2.
      expected_penalty_predicate = np.array([0, 0, 0, 0, 1, 0, 1, 0, 0, 0],
                                            dtype=np.float32)
      expected_constraint_predicate = np.array([0, 1, 0, 1, 0, 0, 0, 0, 0, 1],
                                               dtype=np.float32)
      self.assertAllEqual(
          expected_penalty_predicate,
          session.run(context2.penalty_predicate.tensor(structure_memoizer)))
      self.assertAllEqual(
          expected_constraint_predicate,
          session.run(context2.constraint_predicate.tensor(structure_memoizer)))

  def test_and(self):
    """Tests `SubsettableContext`'s logical AND operator."""
    context1, context2 = create_contexts()
    structure_memoizer = {
        defaults.DENOMINATOR_LOWER_BOUND_KEY: 0.0,
        defaults.GLOBAL_STEP_KEY: tf.compat.v2.Variable(0, dtype=tf.int32)
    }

    and_context = context1 & context2

    with self.wrapped_session() as session:
      # Make sure that AND applies only to the top-level subset.
      expected_penalty_predicate = np.array([0, 0, 0, 0, 1, 0, 0, 0, 0, 0],
                                            dtype=np.float32)
      expected_constraint_predicate = np.array([0, 1, 0, 0, 0, 0, 0, 0, 0, 1],
                                               dtype=np.float32)
      self.assertAllEqual(
          expected_penalty_predicate,
          session.run(and_context.penalty_predicate.tensor(structure_memoizer)))
      self.assertAllEqual(
          expected_constraint_predicate,
          session.run(
              and_context.constraint_predicate.tensor(structure_memoizer)))

  def test_or(self):
    """Tests `SubsettableContext`'s logical OR operator."""
    context1, context2 = create_contexts()
    structure_memoizer = {
        defaults.DENOMINATOR_LOWER_BOUND_KEY: 0.0,
        defaults.GLOBAL_STEP_KEY: tf.compat.v2.Variable(0, dtype=tf.int32)
    }

    or_context = context1 | context2

    with self.wrapped_session() as session:
      # Make sure that OR applies only to the top-level subset.
      expected_penalty_predicate = np.array([0, 0, 1, 0, 1, 0, 1, 0, 0, 0],
                                            dtype=np.float32)
      expected_constraint_predicate = np.array([0, 1, 0, 1, 0, 0, 0, 1, 0, 1],
                                               dtype=np.float32)
      self.assertAllEqual(
          expected_penalty_predicate,
          session.run(or_context.penalty_predicate.tensor(structure_memoizer)))
      self.assertAllEqual(
          expected_constraint_predicate,
          session.run(
              or_context.constraint_predicate.tensor(structure_memoizer)))

  def test_one_hot_labels(self):
    """Tests "_one_hot_labels" function."""
    structure_memoizer = {
        defaults.DENOMINATOR_LOWER_BOUND_KEY: 0.0,
        defaults.GLOBAL_STEP_KEY: tf.compat.v2.Variable(0, dtype=tf.int32)
    }
    one_hot_labels = [[0.1, 0.9], [0.4, 0.6]]
    index_labels = [0, 1, 3, 2, 3, 0]
    index_one_hot_labels = [
        [1.0, 0.0, 0.0, 0.0],
        [0.0, 1.0, 0.0, 0.0],
        [0.0, 0.0, 0.0, 1.0],
        [0.0, 0.0, 1.0, 0.0],
        [0.0, 0.0, 0.0, 1.0],
        [1.0, 0.0, 0.0, 0.0],
    ]

    # Trying to convert a Tensor with <2 columns should fail.
    with self.assertRaises(ValueError):
      with self.wrapped_session() as session:
        _ = session.run(
            subsettable_context._one_hot_labels(one_hot_labels,
                                                1)(structure_memoizer))

    # Trying to convert a Tensor with too many columns should fail.
    with self.assertRaises(ValueError):
      with self.wrapped_session() as session:
        _ = session.run(
            subsettable_context._one_hot_labels(one_hot_labels,
                                                3)(structure_memoizer))

    # The above cases with num_classes=0 should succeed.
    with self.wrapped_session() as session:
      actual = session.run(
          subsettable_context._one_hot_labels(one_hot_labels,
                                              2)(structure_memoizer))
    self.assertAllClose(one_hot_labels, actual, rtol=0, atol=1e-6)

    # Converting from index sets should succeed.
    with self.wrapped_session() as session:
      actual = session.run(
          subsettable_context._one_hot_labels(index_labels,
                                              4)(structure_memoizer))
    self.assertAllClose(index_one_hot_labels, actual, rtol=0, atol=1e-6)


if __name__ == "__main__":
  tf.test.main()
