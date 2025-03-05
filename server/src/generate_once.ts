import { SessionManager } from "./session_manager";
import { Command } from "@commander-js/extra-typings";

const program = new Command()
    .option("-v, --visitor-data <visitordata>")
    .option("-d, --data-sync-id <data-sync-id>")
    .option("-p, --proxy <proxy-all>")
    .option("--verbose");

program.parse();
const options = program.opts();

(async () => {
    const visitorData = options.visitorData;
    const dataSyncId = options.dataSyncId;
    const proxy = options.proxy || "";
    const verbose = options.verbose || false;
    let visitIdentifier: string;

    const sessionManager = new SessionManager(verbose);
    function log(msg: string) {
        if (verbose) console.log(msg);
    }

    if (dataSyncId) {
        log(`Received request for data sync ID: '${dataSyncId}'`);
        visitIdentifier = dataSyncId;
    } else if (visitorData) {
        log(`Received request for visitor data: '${visitorData}'`);
        visitIdentifier = visitorData;
    } else {
        log(`Received request for visitor data, grabbing from Innertube`);
        const generatedVisitorData = await sessionManager.generateVisitorData();
        if (!generatedVisitorData) process.exit(1);
        log(`Generated visitor data: ${generatedVisitorData}`);
        visitIdentifier = generatedVisitorData;
    }

    try {
        const sessionData = await sessionManager.generatePoToken(
            visitIdentifier,
            proxy,
        );
        console.log(JSON.stringify(sessionData));
    } catch (e) {
        console.error(
            `Failed while generating POT. err.name = ${e.name}. err.message = ${e.message}. err.stack = ${e.stack}`,
        );
        console.log(JSON.stringify({}));
        process.exit(1);
    }
})();
