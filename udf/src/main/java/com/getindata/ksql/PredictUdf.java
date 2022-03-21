package com.getindata.ksql;

import io.confluent.ksql.function.udf.Udf;
import io.confluent.ksql.function.udf.UdfDescription;
import io.confluent.ksql.function.udf.UdfParameter;

import ml.combust.mleap.runtime.MleapContext;
import ml.combust.mleap.runtime.frame.DefaultLeapFrame;
import ml.combust.mleap.runtime.frame.Row;
import ml.combust.mleap.runtime.javadsl.ContextBuilder;
import ml.combust.mleap.runtime.javadsl.LeapFrameBuilder;
import ml.combust.mleap.runtime.javadsl.LeapFrameSupport;
import org.apache.kafka.common.Configurable;

import java.util.ArrayList;
import java.util.Arrays;
import java.util.List;
import java.util.Map;
import java.util.concurrent.ConcurrentHashMap;

@UdfDescription(name = "predict",
        author = "Mariusz",
        version = "1.0",
        description = "Applies Mleap model stored in Mlflow")
public class PredictUdf implements Configurable {
    private Map<String, MLModel> models;
    private LeapFrameSupport leapFrameSupport = new LeapFrameSupport();
    private LeapFrameBuilder frameBuilder = new LeapFrameBuilder();
    private MlflowModelResolver modelResolver;

    @Override
    public void configure(final Map<String, ?> map) {
        models = new ConcurrentHashMap<>();
        String mlflowUrl = System.getenv("MLFLOW_URL");
        MleapContext mleapContext = new ContextBuilder().createMleapContext();
        this.modelResolver = new MlflowModelResolver(mlflowUrl, mleapContext, frameBuilder);
    }

    @Udf(description = "Prediction using model name, categorical params and int values")
    public String run(@UdfParameter String modelName, @UdfParameter List<String> stringParams,
                      @UdfParameter List<Integer> intParams) {
        try {
            if (!models.containsKey(modelName)) {
                downloadModel(modelName);
            }

            MLModel model = models.get(modelName);
            List<Object> params = new ArrayList();
            for (String stringParam : stringParams) {
                params.add(stringParam);
            }
            for (Integer intParam : intParams) {
                params.add(intParam);
            }
            Row row = frameBuilder.createRowFromIterable(params);
            DefaultLeapFrame frame = frameBuilder.createFrame(model.getInputSchema(), Arrays.asList(row));
            DefaultLeapFrame result = model.getPipeline().transform(frame).get();
            String prediction = leapFrameSupport.select(result, Arrays.asList(model.getOutputColumn())).dataset().head().getString(0);
            return prediction;
        } catch (Exception e) {
            e.printStackTrace();
            return null;
        }
    }

    private void downloadModel(String modelName) {
        models.put(modelName, this.modelResolver.get(modelName));
    }

}