package com.getindata.ksql;

import ml.combust.mleap.core.types.StructType;
import ml.combust.mleap.runtime.frame.Transformer;

public class MLModel {
    private Transformer pipeline;
    private StructType inputSchema;
    private String outputColumn;

    public Transformer getPipeline() {
        return pipeline;
    }

    public StructType getInputSchema() {
        return inputSchema;
    }

    public String getOutputColumn() {
        return outputColumn;
    }

    public MLModel() {}

    public void setPipeline(Transformer pipeline) {
        this.pipeline = pipeline;
    }

    public void setInputSchema(StructType inputSchema) {
        this.inputSchema = inputSchema;
    }

    public void setOutputColumn(String outputColumn) {
        this.outputColumn = outputColumn;
    }
}
