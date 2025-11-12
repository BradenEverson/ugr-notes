


    // !!! This file is generated using emlearn !!!

    #include <stdint.h>
    

static inline int32_t binary_dt_tree_0(const int16_t *features, int32_t features_length) {
          if (features[8] < 23) {
              if (features[7] < 3) {
                  return 1;
              } else {
                  if (features[1] < 261) {
                      return 0;
                  } else {
                      if (features[11] < 0) {
                          if (features[3] < 989) {
                              return 0;
                          } else {
                              if (features[11] < 0) {
                                  if (features[1] < 6722) {
                                      if (features[0] < 32502) {
                                          return 1;
                                      } else {
                                          return 0;
                                      }
                                  } else {
                                      if (features[11] < 0) {
                                          return 1;
                                      } else {
                                          return 0;
                                      }
                                  }
                              } else {
                                  return 0;
                              }
                          }
                      } else {
                          if (features[11] < 0) {
                              if (features[4] < 4811) {
                                  if (features[2] < 14909) {
                                      if (features[11] < 0) {
                                          return 0;
                                      } else {
                                          return 1;
                                      }
                                  } else {
                                      if (features[1] < 8750) {
                                          return 1;
                                      } else {
                                          return 0;
                                      }
                                  }
                              } else {
                                  return 0;
                              }
                          } else {
                              if (features[11] < 0) {
                                  return 0;
                              } else {
                                  if (features[1] < 831) {
                                      if (features[7] < 463) {
                                          return 1;
                                      } else {
                                          return 1;
                                      }
                                  } else {
                                      if (features[1] < 25377) {
                                          return 0;
                                      } else {
                                          return 1;
                                      }
                                  }
                              }
                          }
                      }
                  }
              }
          } else {
              if (features[8] < 30) {
                  if (features[0] < 21502) {
                      return 0;
                  } else {
                      return 1;
                  }
              } else {
                  if (features[2] < 57285) {
                      return 0;
                  } else {
                      if (features[11] < 0) {
                          return 0;
                      } else {
                          return 1;
                      }
                  }
              }
          }
        }
        

int32_t binary_dt_predict(const int16_t *features, int32_t features_length) {

        int32_t votes[2] = {0,};
        int32_t _class = -1;

        _class = binary_dt_tree_0(features, features_length); votes[_class] += 1;
    
        int32_t most_voted_class = -1;
        int32_t most_voted_votes = 0;
        for (int32_t i=0; i<2; i++) {

            if (votes[i] > most_voted_votes) {
                most_voted_class = i;
                most_voted_votes = votes[i];
            }
        }
        return most_voted_class;
    }
    

int binary_dt_predict_proba(const int16_t *features, int32_t features_length, float *out, int out_length) {

        int32_t _class = -1;

        for (int i=0; i<out_length; i++) {
            out[i] = 0.0f;
        }

        _class = binary_dt_tree_0(features, features_length); out[_class] += 1.0f;
    
        // compute mean
        for (int i=0; i<out_length; i++) {
            out[i] = out[i] / 1;
        }
        return 0;
    }
    