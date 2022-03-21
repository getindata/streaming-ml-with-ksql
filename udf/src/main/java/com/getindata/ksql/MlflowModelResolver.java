package com.getindata.ksql;

import com.fasterxml.jackson.core.type.TypeReference;
import com.fasterxml.jackson.databind.JsonNode;
import com.fasterxml.jackson.databind.ObjectMapper;
import com.fasterxml.jackson.dataformat.yaml.YAMLFactory;
import ml.combust.bundle.BundleFile;
import ml.combust.bundle.dsl.Bundle;
import ml.combust.mleap.core.types.StructField;
import ml.combust.mleap.core.types.StructType;
import ml.combust.mleap.runtime.MleapContext;
import ml.combust.mleap.runtime.frame.Transformer;
import ml.combust.mleap.runtime.javadsl.LeapFrameBuilder;
import org.mlflow.tracking.MlflowClient;
import org.mlflow_project.apachehttp.HttpEntity;
import org.mlflow_project.apachehttp.client.methods.CloseableHttpResponse;
import org.mlflow_project.apachehttp.client.methods.HttpGet;
import org.mlflow_project.apachehttp.impl.client.CloseableHttpClient;
import org.mlflow_project.apachehttp.impl.client.HttpClients;
import org.mlflow_project.apachehttp.util.EntityUtils;

import java.io.FileOutputStream;
import java.io.IOException;
import java.nio.file.Files;
import java.nio.file.Path;
import java.util.ArrayList;
import java.util.Arrays;
import java.util.List;

public class MlflowModelResolver {

    private final MlflowClient client;
    private String mlflowUrl;
    private MleapContext mleapContext;
    private LeapFrameBuilder frameBuilder;

    public MlflowModelResolver(String mlflowUrl, MleapContext mleapContext, LeapFrameBuilder frameBuilder) {
        this.mlflowUrl = mlflowUrl;
        this.mleapContext = mleapContext;
        this.frameBuilder = frameBuilder;
        this.client = new MlflowClient(this.mlflowUrl);
    }

    public MLModel get(String modelName) {
        try {
            String prodRunId = getProdRunId(modelName);
            MLModel model = new MLModel();
            model.setPipeline(deserializeMleapBundle(prodRunId));
            ModelSignature modelSignature = getModelSignature(prodRunId);
            model.setInputSchema(extractInputSchema(modelSignature));
            model.setOutputColumn(extractOutputColumnName(modelSignature));
            return model;
        } catch (Exception e) {
            throw new RuntimeException("Can't download model " + modelName, e);
        }
    }

    private String extractOutputColumnName(ModelSignature modelSignature) {
        return modelSignature.outputs.get(0).name;
    }

    private StructType extractInputSchema(ModelSignature modelSignature) {
        ArrayList<StructField> fields = new ArrayList();
        for (ModelInputField inputField : modelSignature.inputs) {
            if (inputField.type.equals("string")) {
                fields.add(frameBuilder.createField(inputField.name, frameBuilder.createString()));
            } else if (inputField.type.equals("integer")) {
                fields.add(frameBuilder.createField(inputField.name, frameBuilder.createInt()));
            } else if(inputField.type.equals("long")) {
                fields.add(frameBuilder.createField(inputField.name, frameBuilder.createInt()));
            } else {
                throw new RuntimeException("Can't map type " + inputField.type);
            }
        }
        return  frameBuilder.createSchema(fields);
    }

    private ModelSignature getModelSignature(String prodRunId) throws IOException {
        try (CloseableHttpClient httpclient = HttpClients.createDefault()) {

            HttpGet getSignature = new HttpGet(String.format("%s/get-artifact?path=mleap-model%%2FMLmodel&run_uuid=%s",
                    mlflowUrl, prodRunId));
            try (CloseableHttpResponse response1 = httpclient.execute(getSignature)) {
                JsonNode jsonNode = new ObjectMapper(new YAMLFactory()).readTree(response1.getEntity().getContent());
                List<ModelInputField> inputSchema = new ObjectMapper()
                        .readValue(jsonNode.get("signature").get("inputs").asText(),
                                new TypeReference<List<ModelInputField>>() {});
                List<ModelInputField> outputSchema = new ObjectMapper()
                        .readValue(jsonNode.get("signature").get("outputs").asText(),
                                new TypeReference<List<ModelInputField>>() {});
                return new ModelSignature(inputSchema, outputSchema);
            }
        }
    }

    private Transformer deserializeMleapBundle(String prodRunId) throws IOException {
        Path tempPath = Files.createTempFile("mleap", prodRunId);
        try (CloseableHttpClient httpclient = HttpClients.createDefault()) {
            HttpGet getModel = new HttpGet(String.format("%s/get-artifact?path=bundle.zip&run_uuid=%s",
                    mlflowUrl, prodRunId));
            try (CloseableHttpResponse response = httpclient.execute(getModel)) {
                try (FileOutputStream bundle = new FileOutputStream(tempPath.toFile())) {
                    HttpEntity entity = response.getEntity();
                    entity.writeTo(bundle);
                    EntityUtils.consume(entity);
                }
            }
        }

        BundleFile bundleFile = BundleFile.apply(String.format("jar:file:%s", tempPath.toString()));
        Bundle<Object> bundle = bundleFile.load(mleapContext).get();
        return (Transformer)bundle.root();
    }

    private String getProdRunId(String modelName) {
        return client.getLatestVersions(modelName, Arrays.asList("Production")).get(0).getRunId();
    }

    private static class ModelSignature {
        public List<ModelInputField> inputs;
        public List<ModelInputField> outputs;

        public ModelSignature(List<ModelInputField> inputs, List<ModelInputField> outputs) {
            this.inputs = inputs;
            this.outputs = outputs;
        }
    }

    private static class ModelInputField {
        public String name;
        public String type;
    }
}
