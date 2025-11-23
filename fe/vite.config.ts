import { dirname, resolve } from "node:path";
import { defineConfig } from "vite";
import { exec } from "child_process";
import fs from "fs";
import crypto from "crypto";

function protobufPlugin() {
  const pyCmd = `python -m grpc_tools.protoc --proto_path=.. --python_out=../ninjamagic/gen --mypy_out=../ninjamagic/gen ../messages.proto`;
  const tsCmd = `npx protoc --ts_out=src/gen --proto_path=.. ../messages.proto --ts_opt=use_proto_field_name`;
  let lastProtoHash = "";
  return {
    name: "vite-plugin-protobuf",
    configureServer(server) {
      const generate = () => {
        const currentProtoHash = crypto
          .createHash("md5")
          .update(fs.readFileSync("../messages.proto"))
          .digest("hex");
        if (currentProtoHash === lastProtoHash) {
          return;
        }
        lastProtoHash = currentProtoHash;
        console.log("Proto schema changed, regenerating Protobuf files...");
        exec(pyCmd, (err) => {
          if (err) console.error("Error generating Python Protobuf:", err);
          else console.log("Python Protobuf files generated successfully.");
        });
        exec(tsCmd, (err) => {
          if (err) console.error("Error generating TypeScript Protobuf:", err);
          else console.log("TypeScript Protobuf files generated successfully.");
        });
      };

      server.watcher.add("../messages.proto");
      server.watcher.on("add", generate);
      server.watcher.on("change", generate);
    },
  };
}

export default defineConfig({
  base: "/static/gen",
  plugins: [protobufPlugin()],
  build: {
    outDir: "../ninjamagic/static/gen",
    emptyOutDir: true,
    rollupOptions: {
      input: {
        main: resolve(__dirname, "index.html"),
        // rail: resolve(__dirname, "rail.html"),
        // typing_test: resolve(__dirname, "typing-test.html"),
      },
    },
  },
});
