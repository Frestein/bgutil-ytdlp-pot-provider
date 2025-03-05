import { SessionManager } from "./session_manager";
import { VERSION } from "./version";
import { Command } from "@commander-js/extra-typings";
import express from "express";
import bodyParser from "body-parser";

const program = new Command().option("-p, --port <PORT>").option("--verbose");

program.parse();
const options = program.opts();

const PORT_NUMBER = options.port || 4416;

const httpServer = express();
httpServer.use(bodyParser.json());

httpServer.listen({
    host: "0.0.0.0",
    port: PORT_NUMBER,
});

console.log(`Started POT server on port ${PORT_NUMBER}`);

const sessionManager = new SessionManager(options.verbose || false);
httpServer.post("/get_pot", async (request, response) => {
    const visitorData = request.body.visitor_data as string;
    const dataSyncId = request.body.data_sync_id as string;
    const proxy: string = request.body.proxy;
    let contentBinding = dataSyncId || visitorData;
    if (dataSyncId)
        console.log('Passing data_sync_id is deprecated, use visitor_data instead');

    if (!contentBinding) {
        const generatedVisitorData = await sessionManager.generateVisitorData();
        if (!generatedVisitorData) {
            response.status(500).send({ error: "Error generating visitor data" });
            return;
        }
        contentBinding = generatedVisitorData;
    }

    try {
        const sessionData = await sessionManager.generatePoToken(
            contentBinding,
            proxy,
        );

        response.send({
            po_token: sessionData.poToken,
            visit_identifier: sessionData.visitIdentifier,
        });
    } catch (e) {
        console.error(
            `Failed while generating POT. err.name = ${e.name}. err.message = ${e.message}. err.stack = ${e.stack}`,
        );
        response.status(500).send({ error: JSON.stringify(e) });
    }
});

httpServer.get("/ping", async (request, response) => {
    response.send({
        logging: options.verbose ? "verbose" : "normal",
        server_uptime: process.uptime(),
        version: VERSION,
    });
});
